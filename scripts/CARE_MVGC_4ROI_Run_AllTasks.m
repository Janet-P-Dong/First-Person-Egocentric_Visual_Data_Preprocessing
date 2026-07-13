function CARE_MVGC_4ROI_Run_AllTasks()
% CARE_MVGC_4ROI_Run_AllTasks
% ------------------------------------------------------------
% Convenience runner for the MARA 4ROI MVGC pipeline.
%
% This is the upstream step to run before interpreting or comparing
% permutation outputs. It builds/loads ELIG, runs REAL MVGC, generates
% pseudo-dyad null results, and writes task-specific summaries.
%
% Outputs are written by CARE_MVGC_4ROI_Run into:
%   /Users/janet/Desktop/Preprocessing/Preprocessing_fNIRS_StepA/Mara/Mara_TaskReady/MARA/ST
%   /Users/janet/Desktop/Preprocessing/Preprocessing_fNIRS_StepA/Mara/Mara_TaskReady/MARA/FT
%
% Usage:
%   CARE_MVGC_4ROI_Run_AllTasks
% ------------------------------------------------------------
clc;
fprintf('Running CARE_MVGC_4ROI_Run for ST...\n');
CARE_MVGC_4ROI_Run('ST');

fprintf('\nRunning CARE_MVGC_4ROI_Run for FT...\n');
CARE_MVGC_4ROI_Run('FT');

fprintf('\nDone. ST and FT MARA MVGC outputs have been generated.\n');
end
