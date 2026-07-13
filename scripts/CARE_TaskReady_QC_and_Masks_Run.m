function CARE_TaskReady_QC_and_Masks_Run(taskReadyDir, outDir)
% CARE_TaskReady_QC_and_Masks_Run
% TaskReady -> Mathematical QC -> GOOD/BAD masks -> GC-ready cleaned signals -> CSV exports
%
% Outputs:
%   QC_MATH/
%     QC_channel_table.csv
%     QC_segment_table.csv
%     <DYAD>_TaskReady_QC.mat
%
% Notes (patched):
% - Older MATLAB compatibility:
%   * NO kurtosis(...,'omitnan')
%   * NO std(...,'omitnan') / mean(...,'omitnan')
% - Fixed struct assignment:
%   * No prealloc with empty struct() for segments (avoids "dissimilar structures")
%
% Negative values are OK; do NOT rectify/abs().
clc;
if nargin < 1 || isempty(taskReadyDir)
    taskReadyDir = '/Users/janet/Desktop/Preprocessing/Preprocessing_fNIRS_StepA/Mara/Mara_TaskReady';
end
if nargin < 2 || isempty(outDir)
    outDir = '/Users/janet/Desktop/Preprocessing/Preprocessing_fNIRS_StepA/Mara/QC_MATH';
end
files = dir(fullfile(taskReadyDir, '*_TaskReady.mat'));
assert(~isempty(files), 'No *_TaskReady.mat found in %s.', taskReadyDir);
OUTDIR = outDir;
if ~exist(OUTDIR,'dir'); mkdir(OUTDIR); end
% ---------------------------
% Settings
% ---------------------------
TASKS = {'B','ST','FT'};
ROLES = {'Parent','Child'};
NCH   = 22;
% Unwanted channels (always excluded from GC)
UNWANTED = [2 4 6 17 19 21];
% ---- QC thresholds (robust defaults) ----
cfg = struct();
cfg.min_sd_ratio      = 0.10; % SD < 10% of median SD -> BAD
cfg.spike_mad_k       = 6;    % spike threshold = k * MAD(diff)
cfg.max_spike_rate    = 0.02; % >2% samples spikes -> BAD
cfg.max_drift_ratio_bad  = 0.08;
cfg.max_drift_ratio_warn = 0.04;
cfg.kurt_z_bad        = 4.0;
cfg.kurt_z_warn       = 2.5;
% Stationarity (optional; Econometrics Toolbox for adftest)
cfg.do_adf       = true;
cfg.adf_alpha    = 0.05;
cfg.adf_fail_bad = true;
% Mask application:
%   'nan'    keeps 22 columns, sets dropped to NaN
%   'remove' physically removes dropped columns (dimension changes)
cfg.apply_mode = 'nan';
% Keep policy:
%   keep GOOD only (recommended default)
cfg.keep_borderline = false;  % if true, keep BORDERLINE too
% CSV export
cfg.write_csv = true;
% ---------------------------
% Fixed schemas
% ---------------------------
QC_HEADER = { ...
    'Dyad','File','Task','SegIndex','Role','Channel','Label','KeepMask', ...
    'SD','SD_Ratio','SpikeRate','DriftRatio','Kurtosis','KurtZ','ADF_p','ADF_pass' ...
};
N_COL_QC = numel(QC_HEADER);
SEG_HEADER = { ...
    'Dyad','File','Task','SegIndex','fs', ...
    'Parent_nGOOD','Parent_nBORDER','Parent_nBAD','Parent_keepPct', ...
    'Child_nGOOD','Child_nBORDER','Child_nBAD','Child_keepPct' ...
};
N_COL_SEG = numel(SEG_HEADER);
% ---------------------------
% Accumulators (cells only)
% ---------------------------
T_all = cell(0, N_COL_QC);   % channel-level
T_seg = cell(0, N_COL_SEG);  % segment-level
fprintf('=== CARE TaskReady QC -> Masks -> GC prep ===\n');
for f = 1:numel(files)
    matfile = files(f).name;
    matpath = fullfile(taskReadyDir, matfile);
    S = load(matpath);
    assert(isfield(S,'outTask') && isstruct(S.outTask), ...
        'File %s is not a valid TaskReady (missing outTask).', matfile);
    dyad = upper(matfile(1:3));
    fprintf('\n=== QC RUN: %s ===\n', matfile);
    outQC = struct();
    outQC.file = matfile;
    outQC.dyad = dyad;
    outQC.UNWANTED = UNWANTED;
    outQC.cfg = cfg;
    outQC.tasks = struct();
    for ti = 1:numel(TASKS)
        task = TASKS{ti};
        if ~isfield(S.outTask, task) || isempty(S.outTask.(task))
            continue;
        end
        segs = S.outTask.(task);
        assert(isstruct(segs), '%s %s: outTask.%s is not a struct.', dyad, matfile, task);
        nSeg = numel(segs);
        % IMPORTANT PATCH: do NOT preallocate with struct() (causes dissimilar structure assignment)
        % We'll grow the struct array safely via assignment.
        for k = 1:nSeg
            seg = segs(k);
            % fs
            if isfield(seg,'fs')
                fs = seg.fs;
            elseif isfield(S,'fs')
                fs = S.fs;
            else
                fs = NaN;
            end
            segQC = struct();
            segQC.fs = fs;
            segQC.task = task;
            segQC.segIndex = k;
            segQC.role = struct();
            % Segment summary counters
            parentCounts = struct('GOOD',NaN,'BORDER',NaN,'BAD',NaN,'keepPct',NaN);
            childCounts  = struct('GOOD',NaN,'BORDER',NaN,'BAD',NaN,'keepPct',NaN);
            for ri = 1:numel(ROLES)
                role = ROLES{ri};
                [Xhbo, Xhbr] = fetch_taskready_hb(seg, role);
                if isempty(Xhbo)
                    continue;
                end
                assert(size(Xhbo,2) == NCH, ...
                    'Expected 22 channels. Got %d in %s %s seg %d (%s).', size(Xhbo,2), dyad, task, k, role);
                % ---- compute metrics (HbO) ----
                metrics = qc_metrics_per_channel_compat(Xhbo, fs, cfg);
                % mark unwanted
                metrics.is_unwanted = false(1,NCH);
                metrics.is_unwanted(UNWANTED) = true;
                % ---- classify ----
                labels = classify_channels(metrics, cfg); % strings(1,NCH)
                labels(UNWANTED) = "BAD_UNWANTED";
                if cfg.keep_borderline
                    keepMask = ismember(labels, ["GOOD","BORDERLINE"]);
                else
                    keepMask = (labels == "GOOD");
                end
                keepMask(UNWANTED) = false;
                % ---- apply mask to HbO/HbR ----
                [Xhbo_clean, Xhbr_clean] = apply_mask(Xhbo, Xhbr, keepMask, cfg.apply_mode);
                % store
                segQC.role.(role).labels   = labels;
                segQC.role.(role).keepMask = keepMask;
                segQC.role.(role).metrics  = metrics;
                segQC.role.(role).hbo_clean = Xhbo_clean;
                if ~isempty(Xhbr_clean)
                    segQC.role.(role).hbr_clean = Xhbr_clean;
                end
                % ---- update segment summary ----
                nGood   = sum(labels=="GOOD");
                nBorder = sum(labels=="BORDERLINE");
                nBad    = sum(startsWith(labels,"BAD")); % includes BAD_UNWANTED
                keepPct = 100 * sum(keepMask) / NCH;
                if strcmpi(role,'Parent')
                    parentCounts.GOOD   = nGood;
                    parentCounts.BORDER = nBorder;
                    parentCounts.BAD    = nBad;
                    parentCounts.keepPct = keepPct;
                else
                    childCounts.GOOD   = nGood;
                    childCounts.BORDER = nBorder;
                    childCounts.BAD    = nBad;
                    childCounts.keepPct = keepPct;
                end
                % ---- append channel-level rows (strict schema) ----
                for ch = 1:NCH
                    row = { ...
                        dyad, matfile, task, k, role, ch, char(labels(ch)), logical(keepMask(ch)), ...
                        metrics.sd(ch), metrics.sd_ratio(ch), metrics.spike_rate(ch), ...
                        metrics.drift_ratio(ch), metrics.kurtosis(ch), metrics.kurt_z(ch), ...
                        metrics.adf_p(ch), logical(metrics.adf_pass(ch)) ...
                    };
                    assert(numel(row) == N_COL_QC, ...
                        'QC row width mismatch: got %d expected %d (dyad=%s task=%s seg=%d role=%s ch=%d)', ...
                        numel(row), N_COL_QC, dyad, task, k, role, ch);
                    T_all(end+1, :) = row;
                end
            end
            % ---- append segment-level row (strict schema) ----
            segRow = { ...
                dyad, matfile, task, k, fs, ...
                parentCounts.GOOD, parentCounts.BORDER, parentCounts.BAD, parentCounts.keepPct, ...
                childCounts.GOOD,  childCounts.BORDER,  childCounts.BAD,  childCounts.keepPct ...
            };
            assert(numel(segRow) == N_COL_SEG, ...
                'SEG row width mismatch: got %d expected %d (dyad=%s task=%s seg=%d)', ...
                numel(segRow), N_COL_SEG, dyad, task, k);
            T_seg(end+1, :) = segRow;
            % ---- SAFE struct assignment (no dissimilar-structure issue) ----
            if ~isfield(outQC.tasks, task) || ~isfield(outQC.tasks.(task), 'segments') || isempty(outQC.tasks.(task).segments)
                outQC.tasks.(task).segments = segQC;   % first assignment creates correct fields
            else
                outQC.tasks.(task).segments(k) = segQC;
            end
        end
    end
    save(fullfile(OUTDIR, sprintf('%s_TaskReady_QC.mat', dyad)), 'outQC', '-v7.3');
    fprintf('✅ Saved: %s\n', fullfile(OUTDIR, sprintf('%s_TaskReady_QC.mat', dyad)));
end
% ---------------------------
% Export CSV
% ---------------------------
if cfg.write_csv
    % ---- Channel-level export ----
    out1 = fullfile(OUTDIR,'QC_channel_table.csv');
    export_cell_as_csv(T_all, QC_HEADER, out1);
    % ---- Segment-level export ----
    out2 = fullfile(OUTDIR,'QC_segment_table.csv');
    export_cell_as_csv(T_seg, SEG_HEADER, out2);
    fprintf('\n✅ CSV exported:\n  - %s\n  - %s\n', out1, out2);
end
fprintf('\nDONE.\n');
end
%% ============================================================
% Helper: fetch Hb matrices from TaskReady segment struct
%% ============================================================
function [Xhbo, Xhbr] = fetch_taskready_hb(seg, role)
Xhbo = [];
Xhbr = [];
if strcmpi(role,'Parent')
    if isfield(seg,'p_hbo'); Xhbo = seg.p_hbo; end
    if isfield(seg,'p_hbr'); Xhbr = seg.p_hbr; end
else
    if isfield(seg,'c_hbo'); Xhbo = seg.c_hbo; end
    if isfield(seg,'c_hbr'); Xhbr = seg.c_hbr; end
end
end
%% ============================================================
% QC metrics per channel (HbO) - backward compatible NaN handling
%% ============================================================
function M = qc_metrics_per_channel_compat(X, fs, cfg) %#ok<INUSD>
% X: [T x nCh]
[T,nCh] = size(X);
M = struct();
M.sd = zeros(1,nCh);
M.sd_ratio = zeros(1,nCh);
M.spike_rate = zeros(1,nCh);
M.drift_ratio = zeros(1,nCh);
M.kurtosis = nan(1,nCh);
M.kurt_z = nan(1,nCh);
M.adf_p = nan(1,nCh);
M.adf_pass = false(1,nCh);
% ---- SD baseline (NaN-safe, old MATLAB compatible) ----
sds = nan(1,nCh);
for ch = 1:nCh
    xc = X(:,ch);
    xc = xc(~isnan(xc));
    if isempty(xc)
        sds(ch) = 0;
    else
        sds(ch) = std(xc,0);
    end
end
medSD = median(sds(sds>0));
if isempty(medSD) || medSD == 0 || isnan(medSD)
    medSD = 1;
end
% ---- Kurtosis baseline (NaN-safe, old MATLAB compatible) ----
kurtVals = nan(1,nCh);
for ch = 1:nCh
    xc = X(:,ch);
    xc = xc(~isnan(xc));
    if numel(xc) < 4
        kurtVals(ch) = NaN;
    else
        kurtVals(ch) = kurtosis(xc,0);
    end
end
kMed = median(kurtVals(~isnan(kurtVals)));
if isempty(kMed) || isnan(kMed), kMed = 0; end
kMAD = mad(kurtVals(~isnan(kurtVals)),1);
if isempty(kMAD) || kMAD == 0 || isnan(kMAD)
    kMAD = 1;
end
hasADF = cfg.do_adf && exist('adftest','file')==2;
for ch = 1:nCh
    x = X(:,ch);
    xc = x(~isnan(x));
    % SD
    sd = sds(ch);
    M.sd(ch) = sd;
    M.sd_ratio(ch) = sd / medSD;
    % Spike rate (MAD of diff)
    if numel(xc) < 2
        M.spike_rate(ch) = 0;
    else
        dx = diff(xc);
        thr = cfg.spike_mad_k * mad(dx,1);
        if thr == 0 || isnan(thr)
            M.spike_rate(ch) = 0;
        else
            M.spike_rate(ch) = mean(abs(dx) > thr);
        end
    end
    % Drift ratio (|slope| / SD) using sample index
    if sd == 0 || numel(xc) < 5
        M.drift_ratio(ch) = Inf;
    else
        tt = (1:numel(xc))';
        p = polyfit(tt, xc, 1);
        M.drift_ratio(ch) = abs(p(1)) / sd;
    end
    % Kurtosis + robust Z
    kv = kurtVals(ch);
    M.kurtosis(ch) = kv;
    M.kurt_z(ch) = (kv - kMed) / kMAD;
    % ADF test
    if hasADF && numel(xc) > 10
        try
            [h,pval] = adftest(xc,'Alpha',cfg.adf_alpha);
            M.adf_p(ch) = pval;
            M.adf_pass(ch) = (h==1);
        catch
            M.adf_p(ch) = NaN;
            M.adf_pass(ch) = false;
        end
    end
end
end
%% ============================================================
% Channel classification
%% ============================================================
function labels = classify_channels(M, cfg)
nCh = numel(M.sd);
labels = strings(1,nCh);
for ch = 1:nCh
    isFlat = (M.sd_ratio(ch) < cfg.min_sd_ratio);
    isSpiky = (M.spike_rate(ch) > cfg.max_spike_rate);
    isDriftBad  = (M.drift_ratio(ch) > cfg.max_drift_ratio_bad);
    isDriftWarn = (M.drift_ratio(ch) > cfg.max_drift_ratio_warn);
    isKurtBad  = (~isnan(M.kurt_z(ch)) && (M.kurt_z(ch) > cfg.kurt_z_bad));
    isKurtWarn = (~isnan(M.kurt_z(ch)) && (M.kurt_z(ch) > cfg.kurt_z_warn));
    adfFail = false;
    if ~isnan(M.adf_p(ch))
        adfFail = ~M.adf_pass(ch);
    end
    if isFlat || isSpiky || isKurtBad || (isDriftBad && (cfg.adf_fail_bad || adfFail))
        labels(ch) = "BAD";
    elseif isDriftWarn || isKurtWarn || adfFail
        labels(ch) = "BORDERLINE";
    else
        labels(ch) = "GOOD";
    end
end
end
%% ============================================================
% Apply keep mask
%% ============================================================
function [Xhbo_clean, Xhbr_clean] = apply_mask(Xhbo, Xhbr, keepMask, mode)
Xhbo_clean = Xhbo;
Xhbr_clean = Xhbr;
switch lower(mode)
    case 'nan'
        bad = ~keepMask;
        Xhbo_clean(:, bad) = NaN;
        if ~isempty(Xhbr_clean)
            Xhbr_clean(:, bad) = NaN;
        end
    case 'remove'
        Xhbo_clean = Xhbo(:, keepMask);
        if ~isempty(Xhbr_clean)
            Xhbr_clean = Xhbr(:, keepMask);
        end
    otherwise
        error('Unknown apply_mode: %s (use ''nan'' or ''remove'')', mode);
end
end
function export_cell_as_csv(C, header, outfile)
% export_cell_as_csv
% Robust CSV exporter that works even on older MATLAB versions.
% Tries: cell2table+writetable; if unavailable, uses writecell; if unavailable, uses manual fprintf.
% Ensure C is a cell matrix with correct width
nCol = numel(header);
if isempty(C)
    % export header only
    try
        writecell(header, outfile);
    catch
        % manual header write
        fid = fopen(outfile,'w');
        assert(fid~=-1, 'Cannot open %s for writing.', outfile);
        fprintf(fid, '%s', header{1});
        for j=2:nCol
            fprintf(fid, ',%s', header{j});
        end
        fprintf(fid, '\n');
        fclose(fid);
    end
    return;
end
assert(iscell(C), 'Expected a cell array for export.');
assert(size(C,2) == nCol, 'Export cell width mismatch: got %d, expected %d', size(C,2), nCol);
% Try cell2table + writetable
if exist('cell2table','file')==2
    try
        T = cell2table(C, 'VariableNames', header);
        if istable(T)
            writetable(T, outfile);
            return;
        end
    catch
        % fall through
    end
end
% Try writecell
if exist('writecell','file')==2
    try
        writecell([header; C], outfile);
        return;
    catch
        % fall through
    end
end
% Manual CSV writing (last resort)
fid = fopen(outfile,'w');
assert(fid~=-1, 'Cannot open %s for writing.', outfile);
% header
fprintf(fid, '%s', header{1});
for j=2:nCol
    fprintf(fid, ',%s', header{j});
end
fprintf(fid, '\n');
% rows
for i=1:size(C,1)
    for j=1:nCol
        v = C{i,j};
        if isstring(v) || ischar(v)
            s = char(v);
            s = strrep(s,'"','""'); % escape quotes
            fprintf(fid, '"%s"', s);
        elseif islogical(v)
            fprintf(fid, '%d', v);
        elseif isnumeric(v)
            if isempty(v) || isnan(v)
                fprintf(fid, '');
            else
                fprintf(fid, '%.10g', v);
            end
        else
            % fallback to string conversion
            s = strrep(evalc('disp(v)'), sprintf('\n'), ' ');
            s = strtrim(s);
            s = strrep(s,'"','""');
            fprintf(fid, '"%s"', s);
        end
        if j < nCol
            fprintf(fid, ',');
        end
    end
    fprintf(fid, '\n');
end
fclose(fid);
end
