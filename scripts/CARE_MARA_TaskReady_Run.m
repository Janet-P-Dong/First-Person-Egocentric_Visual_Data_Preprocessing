function CARE_MARA_TaskReady_Run(workDir)
% CARE_MARA_TaskReady_Run
% Standardized MARA + TaskReady generation stage.
%
% Run from, or point workDir to, the folder containing:
%   *.txt
%   parent.SD
%   fNIRS_Task_Marker_Manipulated.csv
%
% Outputs in workDir:
%   *_Convert2DoD.mat
%   *_MARA_Conc.mat
%   QC_Plots/*.png
%   *_TaskReady.mat
if nargin < 1 || isempty(workDir)
    workDir = '/Users/janet/Desktop/Preprocessing/Preprocessing_fNIRS_StepA/Mara/Mara_TaskReady';
end
oldDir = pwd;
cleanupObj = onCleanup(@() cd(oldDir));
cd(workDir);

%% ============================================================
% CARE fNIRS Pipeline (TXT conc -> dc -> MARA -> QC Plots -> Task Seg (B/ST/FT) -> (optional) WTC -> GC-ready)
% ============================================================
% PATCHES INCLUDED:
% 1) MARA 3D->2D reshape patch (run MARA on nT x 66, reshape back to nT x 3 x 22)
% 2) Stage B2: QC plots BEFORE vs AFTER (Parent/Child) in different figures
%
% OUTPUTS:
% 1) *_Convert2DoD.mat    : contains dc.p, dc.c, markers (data.s), fs, SD, etc.
% 2) *_MARA_Conc.mat      : continuous motion-corrected concentration (dc_p_mara, dc_c_mara, p/c Hb matrices)
% 3) QC_Plots/*.png       : before/after plots (Parent/Child)
% 4) *_TaskReady.mat      : B/ST/FT segments (WTC optional) for GC
% ============================================================

%% =======================
% User settings
%% =======================
clc;

USE_WTC     = true;   % set false if you want MARA-only segments
WTC_ALPHA   = 0.5;    % your wtc_denoise alpha
BUFFER_SEC  = 15;     % 10–20 sec recommended for task-wise ops

% MARA parameters
MARA_L_SEC      = 1.0;    % moving-std window length in seconds
MARA_TH_MULT    = 3;      % threshold multiplier
MARA_ALPHA_SEC  = 6;      % LOESS smoothing window in seconds

% Marker CSV
MARKER_CSV = 'fNIRS_Task_Marker_Manipulated.csv';

% QC plotting settings
DO_QC_PLOTS  = true;          % true -> generate before/after plots
QC_DIR       = 'QC_Plots';    % folder to save plots
QC_CHS       = [];            % [] = all 22 channels; or e.g. [1 4 7 10]
QC_CHROMO    = 1;             % 1=HbO, 2=HbR, 3=HbT

%% =======================
% Stage A: TXT (conc) -> dc (nT x 3 x 22) for parent/child
% Input : *.txt
% Output: *_Convert2DoD.mat
%% =======================
files = dir('*.txt');
if isempty(files)
    fprintf('No *.txt found. Skipping Stage A.\n');
else
    load('parent.SD','-mat');   % SD must be 22ch layout for parent/child (same geometry)

    fs = 1/0.135;

    % Mean ages (your population means)
    A.p = 34.05;
    A.c = 3.88;

    % PPF from Scholkmann-like model using SD.Lambda (780/805/830)
    ppf.p = 223.3 + 0.05624*A.p.^0.8493 - 5.723e-7*SD.Lambda.^3 + 0.001245*SD.Lambda.^2 - 0.9025*SD.Lambda;
    ppf.c = 223.3 + 0.05624*A.c.^0.8493 - 5.723e-7*SD.Lambda.^3 + 0.001245*SD.Lambda.^2 - 0.9025*SD.Lambda;

    for f = 1:length(files)
        filename = files(f).name;
        name = filename(1:3);

        fprintf('\n[Stage A %d/%d] %s\n', f, length(files), filename);

        fid = fopen(filename,'r');
        assert(fid~=-1, 'Cannot open %s', filename);

        x = textscan(fid,'%s','delimiter','\n');
        fclose(fid);
        x = x{1};

        % ---- Parse numeric rows robustly ----
        Data = [];
        for r = 1:length(x)
            row = str2num(x{r}); %#ok<ST2NM>
            if isnumeric(row) && numel(row) >= 136
                Data = [Data; row(1:136)]; %#ok<AGROW>
            end
        end
        assert(~isempty(Data), 'No numeric data rows found in %s', filename);

        data.t = Data(:,1);   % time (ms)
        data.s = Data(:,2);   % marker
        data.tIncMan.c = ones(size(data.t));
        aux.c = zeros(size(data.t));

        % 132 cols = 44ch * (HbO,HbR,HbT)
        data.pc = Data(:,5:136);

        nT  = size(data.pc,1);
        nCh = 22;

        dc.p = zeros(nT,3,nCh);
        dc.c = zeros(nT,3,nCh);

        % Parent: cols 1:66, Child: cols 67:132
        dc.p(:,1,:) = data.pc(:,  1:3:64);   % HbO
        dc.p(:,2,:) = data.pc(:,  2:3:65);   % HbR
        dc.p(:,3,:) = data.pc(:,  3:3:66);   % HbT

        dc.c(:,1,:) = data.pc(:, 67:3:130);  % HbO
        dc.c(:,2,:) = data.pc(:, 68:3:131);  % HbR
        dc.c(:,3,:) = data.pc(:, 69:3:132);  % HbT

        save([name '_Convert2DoD.mat'], 'A','ppf','fs','Data','data','dc','aux','SD','-v7.3');
        fprintf('✅ Saved %s\n', [name '_Convert2DoD.mat']);
    end
end

%% =======================
% Stage B: MARA on concentration (continuous)
% Input : *_Convert2DoD.mat (dc.p / dc.c)
% Output: *_MARA_Conc.mat
%% =======================
clc;

files = dir('*_Convert2DoD.mat');
if isempty(files)
    error('No *_Convert2DoD.mat found. Run Stage A or check your folder.');
end

for f = 1:length(files)
    load(files(f).name, 'dc','fs','data'); %#ok<LOAD>

    name = files(f).name(1:3);
    fprintf('\n[Stage B %d/%d] MARA continuous for %s\n', f, length(files), name);

    % ---- Configure MARA ----
    cfg = struct();
    cfg.fs = fs;
    cfg.M = struct();

    % ===== Parent MARA (2D reshape patch) =====
    x2 = reshape(dc.p, size(dc.p,1), []);  % nT x 66
    cfg2 = cfg;

    cfg2.M.chs   = 1:size(x2,2);
    cfg2.M.L     = MARA_L_SEC;
    cfg2.M.th    = MARA_TH_MULT;
    cfg2.M.alpha = round(MARA_ALPHA_SEC * fs);

    [y2p, cfgP] = care_spmfnirs_MARA(x2, cfg2);
    dc_p_mara   = reshape(y2p, size(dc.p,1), size(dc.p,2), size(dc.p,3)); % nT x 3 x 22

    % ===== Child MARA (2D reshape patch) =====
    x2 = reshape(dc.c, size(dc.c,1), []);
    cfg2 = cfg;

    cfg2.M.chs   = 1:size(x2,2);
    cfg2.M.L     = MARA_L_SEC;
    cfg2.M.th    = MARA_TH_MULT;
    cfg2.M.alpha = round(MARA_ALPHA_SEC * fs);

    [y2c, cfgC] = care_spmfnirs_MARA(x2, cfg2);
    dc_c_mara   = reshape(y2c, size(dc.c,1), size(dc.c,2), size(dc.c,3));

    out = struct();
    out.cfgP = cfgP;
    out.cfgC = cfgC;
    out.mara = struct('L_sec',MARA_L_SEC,'th_mult',MARA_TH_MULT,'alpha_sec',MARA_ALPHA_SEC);

    % Also store as convenient 2D Hb matrices
    p = struct();
    c = struct();
    p.hbo = squeeze(dc_p_mara(:,1,:));
    p.hbr = squeeze(dc_p_mara(:,2,:));
    p.hbt = squeeze(dc_p_mara(:,3,:));
    c.hbo = squeeze(dc_c_mara(:,1,:));
    c.hbr = squeeze(dc_c_mara(:,2,:));
    c.hbt = squeeze(dc_c_mara(:,3,:));

    save([name '_MARA_Conc.mat'], 'dc_p_mara','dc_c_mara','p','c','fs','out','data','-v7.3');
    fprintf('✅ Saved %s\n', [name '_MARA_Conc.mat']);
end

%% =======================
% Stage B2: QC plots BEFORE vs AFTER (different plots)
% Input : *_Convert2DoD.mat + *_MARA_Conc.mat
% Output: QC_Plots/*.png
%% =======================
if DO_QC_PLOTS
    if exist(QC_DIR,'dir')~=7
        mkdir(QC_DIR);
    end

    convFiles = dir('*_Convert2DoD.mat');
    maraFiles = dir('*_MARA_Conc.mat');
    assert(~isempty(convFiles) && ~isempty(maraFiles), 'Need both Convert2DoD and MARA_Conc to run QC plots.');

    for f = 1:length(convFiles)
        id = upper(convFiles(f).name(1:3));

        if exist([id '_MARA_Conc.mat'],'file')~=2
            fprintf('QC: Missing %s_MARA_Conc.mat, skip QC for %s\n', id, id);
            continue;
        end

        A = load([id '_Convert2DoD.mat'], 'dc','fs');
        B = load([id '_MARA_Conc.mat'], 'p','c');

        % Select chromophore: 1 HbO, 2 HbR, 3 HbT
        rawP  = squeeze(A.dc.p(:,QC_CHROMO,:));  % T x 22
        rawC  = squeeze(A.dc.c(:,QC_CHROMO,:));  % T x 22

        switch QC_CHROMO
            case 1
                maraP = B.p.hbo; maraC = B.c.hbo; chromoName = 'HbO';
            case 2
                maraP = B.p.hbr; maraC = B.c.hbr; chromoName = 'HbR';
            case 3
                maraP = B.p.hbt; maraC = B.c.hbt; chromoName = 'HbT';
            otherwise
                error('QC_CHROMO must be 1(HbO),2(HbR),3(HbT).');
        end

        % Choose channels
        if isempty(QC_CHS)
            chs = 1:size(rawP,2);
        else
            chs = QC_CHS;
        end

        % Parent BEFORE / AFTER in separate figures
        fh1 = plot_with_offset(rawP,  chs, sprintf('%s Parent %s BEFORE (raw)', id, chromoName));
        saveas(fh1, fullfile(QC_DIR, sprintf('%s_parent_%s_before.png', id, lower(chromoName))));
        close(fh1);

        fh2 = plot_with_offset(maraP, chs, sprintf('%s Parent %s AFTER (MARA)', id, chromoName));
        saveas(fh2, fullfile(QC_DIR, sprintf('%s_parent_%s_after.png', id, lower(chromoName))));
        close(fh2);

        % Child BEFORE / AFTER in separate figures
        fh3 = plot_with_offset(rawC,  chs, sprintf('%s Child %s BEFORE (raw)', id, chromoName));
        saveas(fh3, fullfile(QC_DIR, sprintf('%s_child_%s_before.png', id, lower(chromoName))));
        close(fh3);

        fh4 = plot_with_offset(maraC, chs, sprintf('%s Child %s AFTER (MARA)', id, chromoName));
        saveas(fh4, fullfile(QC_DIR, sprintf('%s_child_%s_after.png', id, lower(chromoName))));
        close(fh4);

        fprintf('QC saved for %s (%s)\n', id, chromoName);
    end
end

%% =========================
% Stage C: Segment B / ST / FT only (from MARA output)
% Input : *_MARA_Conc.mat
% Output: <ID>_TaskReady.mat
%% =========================
clc;

MARKER_CSV = 'fNIRS_Task_Marker_Manipulated.csv';

% --- Options ---
USE_WTC    = true;
WTC_ALPHA  = 0.5;
BUFFER_SEC = 15;
MINLEN_WTC = 1000;

assert(exist(MARKER_CSV,'file')==2, 'Marker CSV not found: %s', MARKER_CSV);
T = readtable(MARKER_CSV);

req = {'Dyad','File','StartIndex','EndIndex','Task'};
for i = 1:numel(req)
    assert(any(strcmp(T.Properties.VariableNames, req{i})), 'CSV missing column: %s', req{i});
end

dyad    = upper(strtrim(string(T.Dyad)));
filecol = upper(strtrim(string(T.File)));

ID3 = dyad;
need = (ID3 == "" | ismissing(ID3));
if any(need)
    tmp = extractBefore(filecol + "___", 4);
    ID3(need) = tmp(need);
end

task = upper(strtrim(string(T.Task)));

% Keep only exact B/ST/FT
keepTask = ismember(task, ["B","ST","FT"]);
T = T(keepTask,:);
ID3  = ID3(keepTask);
task = task(keepTask);

StartIndex = T.StartIndex;
EndIndex   = T.EndIndex;

files = dir('*_MARA_Conc.mat');
assert(~isempty(files), 'No *_MARA_Conc.mat found. Run Stage B (MARA) first.');

for f = 1:length(files)
    S = load(files(f).name, 'p','c','fs');
    p = S.p; c = S.c; fs = S.fs;

    name = upper(files(f).name(1:3));
    rows = (ID3 == name);

    if ~any(rows)
        fprintf('Stage C: No marker rows for %s. Skipping.\n', name);
        continue;
    end

    TT_task = task(rows);
    TT_s    = StartIndex(rows);
    TT_e    = EndIndex(rows);

    nT  = size(p.hbo,1);
    buf = round(BUFFER_SEC * fs);

    outTask = struct();

    for r = 1:numel(TT_task)
        taskName = char(TT_task(r));
        iStart   = TT_s(r);
        iEnd     = TT_e(r);

        if iStart < 1 || iEnd > nT || iEnd < iStart
            fprintf('BAD IDX %s %s: [%d %d], nT=%d -> skip\n', name, taskName, iStart, iEnd, nT);
            continue;
        end

        segLen = iEnd - iStart + 1;
        if strcmp(taskName,'B')
            if segLen ~= 443
                fprintf('WARN %s baseline length %d (expected 443). Skip.\n', name, segLen);
                continue;
            end
        else
            if segLen ~= 2222
                fprintf('WARN %s %s length %d (expected 2222). Skip.\n', name, taskName, segLen);
                continue;
            end
        end

        iStartB = max(1, iStart - buf);
        iEndB   = min(nT, iEnd + buf);

        p_hbo = p.hbo(iStartB:iEndB,:);
        p_hbr = p.hbr(iStartB:iEndB,:);
        c_hbo = c.hbo(iStartB:iEndB,:);
        c_hbr = c.hbr(iStartB:iEndB,:);

        if USE_WTC && ~strcmp(taskName,'B')
            if size(p_hbo,1) >= MINLEN_WTC
                try
                    p_hbo = wtc_denoise_mara(p_hbo, WTC_ALPHA);
                    p_hbr = wtc_denoise_mara(p_hbr, WTC_ALPHA);
                    c_hbo = wtc_denoise_mara(c_hbo, WTC_ALPHA);
                    c_hbr = wtc_denoise_mara(c_hbr, WTC_ALPHA);
                catch ME
                    fprintf('WTC failed for %s %s: %s (keep MARA-only)\n', name, taskName, ME.message);
                end
            else
                fprintf('Skip WTC for %s %s (len=%d)\n', name, taskName, size(p_hbo,1));
            end
        end

        keepStart = (iStart - iStartB) + 1;
        keepEnd   = (iEnd   - iStartB) + 1;

        seg = struct();
        seg.p_hbo = p_hbo(keepStart:keepEnd,:);
        seg.p_hbr = p_hbr(keepStart:keepEnd,:);
        seg.c_hbo = c_hbo(keepStart:keepEnd,:);
        seg.c_hbr = c_hbr(keepStart:keepEnd,:);
        seg.idx   = [iStart iEnd];
        seg.fs    = fs;

        if ~isfield(outTask, taskName)
            outTask.(taskName) = seg;
        else
            outTask.(taskName)(end+1) = seg;
        end
    end

    meta = struct();
    meta.USE_WTC    = USE_WTC;
    meta.WTC_ALPHA  = WTC_ALPHA;
    meta.BUFFER_SEC = BUFFER_SEC;
    meta.MINLEN_WTC = MINLEN_WTC;

    save([name '_TaskReady.mat'], 'outTask','meta','fs','-v7.3');
    fprintf('Stage C saved: %s\n', [name '_TaskReady.mat']);
end

%% =========================
% Helper: plot_with_offset (separate plots, channel offsets)
%% =========================
end

function fh = plot_with_offset(signal, chs, ttl)
    time = 1:size(signal,1);

    sig_plot = signal;
    kk = 0;

    for i = 1:numel(chs)
        kk = kk + 1e-6;
        ch = chs(i);
        sig_plot(:,ch) = sig_plot(:,ch) + kk;
    end

    fh = figure('Visible','on');
    plot(time, sig_plot(:,chs));
    xlabel('Time');
    ylabel('Concentration');
    title(ttl);
end
