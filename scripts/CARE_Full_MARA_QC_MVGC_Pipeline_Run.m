function CARE_Full_MARA_QC_MVGC_Pipeline_Run(varargin)
% CARE_Full_MARA_QC_MVGC_Pipeline_Run
% ------------------------------------------------------------
% Standardized runner for the CARE fNIRS pipeline:
%
%   1) MARA + TaskReady generation
%   2) TaskReady mathematical QC + keep masks
%   3) ROI-level MVGC + full ordered pseudo-dyad null
%
% Default paths:
%   TaskReady/data folder:
%     /Users/janet/Desktop/Preprocessing/Preprocessing_fNIRS_StepA/Mara/Mara_TaskReady
%   QC mask folder:
%     /Users/janet/Desktop/Preprocessing/Preprocessing_fNIRS_StepA/Mara/QC_MATH
%
% Usage:
%   CARE_Full_MARA_QC_MVGC_Pipeline_Run
%
% Run only QC + MVGC, leaving existing TaskReady files untouched:
%   CARE_Full_MARA_QC_MVGC_Pipeline_Run('RunMARA', false)
%
% Dry run:
%   CARE_Full_MARA_QC_MVGC_Pipeline_Run('DryRun', true)
% ------------------------------------------------------------
cfg = parse_pipeline_args(varargin{:});

scriptDir = fileparts(mfilename('fullpath'));
addpath(scriptDir);

fprintf('\n=== CARE FULL MARA + QC + MVGC PIPELINE ===\n');
fprintf('TaskReadyDir : %s\n', cfg.TaskReadyDir);
fprintf('QCDir        : %s\n', cfg.QCDir);
fprintf('RunMARA      : %d\n', cfg.RunMARA);
fprintf('RunQC        : %d\n', cfg.RunQC);
fprintf('RunMVGC      : %d\n', cfg.RunMVGC);
fprintf('Tasks        : %s\n', strjoin(cfg.Tasks, ', '));
fprintf('DryRun       : %d\n\n', cfg.DryRun);

assert(exist(cfg.TaskReadyDir, 'dir') == 7, 'TaskReadyDir does not exist: %s', cfg.TaskReadyDir);
if exist(cfg.QCDir, 'dir') ~= 7 && ~cfg.DryRun
    mkdir(cfg.QCDir);
end

assert(exist(fullfile(scriptDir, 'CARE_MARA_TaskReady_Run.m'), 'file') == 2, ...
    'Missing CARE_MARA_TaskReady_Run.m in %s', scriptDir);
assert(exist(fullfile(scriptDir, 'CARE_TaskReady_QC_and_Masks_Run.m'), 'file') == 2, ...
    'Missing CARE_TaskReady_QC_and_Masks_Run.m in %s', scriptDir);
assert(exist(fullfile(scriptDir, 'CARE_MVGC_4ROI_Run.m'), 'file') == 2, ...
    'Missing CARE_MVGC_4ROI_Run.m in %s', scriptDir);

if cfg.DryRun
    fprintf('[DRY RUN] Would run requested stages, but no files will be modified.\n');
    print_expected_outputs(cfg);
    return;
end

if cfg.RunMARA
    fprintf('\n[1/3] MARA + TaskReady generation...\n');
    CARE_MARA_TaskReady_Run(cfg.TaskReadyDir);
else
    fprintf('\n[1/3] MARA + TaskReady generation skipped.\n');
end

if cfg.RunQC
    fprintf('\n[2/3] TaskReady QC + keep masks...\n');
    CARE_TaskReady_QC_and_Masks_Run(cfg.TaskReadyDir, cfg.QCDir);
else
    fprintf('\n[2/3] TaskReady QC + keep masks skipped.\n');
end

if cfg.RunMVGC
    fprintf('\n[3/3] ROI MVGC + pseudo-dyad null...\n');
    for i = 1:numel(cfg.Tasks)
        CARE_MVGC_4ROI_Run(cfg.Tasks{i});
    end
else
    fprintf('\n[3/3] ROI MVGC + pseudo-dyad null skipped.\n');
end

fprintf('\nDONE: standardized CARE pipeline finished.\n');
print_expected_outputs(cfg);
end

function cfg = parse_pipeline_args(varargin)
cfg = struct();
cfg.TaskReadyDir = '/Users/janet/Desktop/Preprocessing/Preprocessing_fNIRS_StepA/Mara/Mara_TaskReady';
cfg.QCDir = '/Users/janet/Desktop/Preprocessing/Preprocessing_fNIRS_StepA/Mara/QC_MATH';
cfg.RunMARA = true;
cfg.RunQC = true;
cfg.RunMVGC = true;
cfg.Tasks = {'ST','FT'};
cfg.DryRun = false;

assert(mod(numel(varargin), 2) == 0, 'Arguments must be name-value pairs.');
for i = 1:2:numel(varargin)
    name = char(varargin{i});
    value = varargin{i+1};
    switch lower(name)
        case 'taskreadydir'
            cfg.TaskReadyDir = char(value);
        case 'qcdir'
            cfg.QCDir = char(value);
        case 'runmara'
            cfg.RunMARA = logical(value);
        case 'runqc'
            cfg.RunQC = logical(value);
        case 'runmvgc'
            cfg.RunMVGC = logical(value);
        case 'tasks'
            cfg.Tasks = cellstr(upper(string(value)));
        case 'dryrun'
            cfg.DryRun = logical(value);
        otherwise
            error('Unknown option: %s', name);
    end
end

cfg.Tasks = cellfun(@char, cellstr(upper(string(cfg.Tasks))), 'UniformOutput', false);
for i = 1:numel(cfg.Tasks)
    assert(any(strcmp(cfg.Tasks{i}, {'ST','FT'})), 'Tasks must be ST and/or FT.');
end
end

function print_expected_outputs(cfg)
fprintf('\nExpected outputs:\n');
fprintf('  TaskReady files : %s/*_TaskReady.mat\n', cfg.TaskReadyDir);
fprintf('  QC masks        : %s/*_TaskReady_QC.mat\n', cfg.QCDir);
for i = 1:numel(cfg.Tasks)
    task = cfg.Tasks{i};
    fprintf('  MVGC %s outputs : %s/MARA/%s/GC_*.csv\n', task, cfg.TaskReadyDir, task);
end
end
