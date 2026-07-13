function CARE_MVGC_FT_4ROI_ComparePermutationOutputs()
% CARE_MVGC_FT_4ROI_ComparePermutationOutputs
% ------------------------------------------------------------
% Compare the original CARE_MVGC_FT_4ROI_Run output against the
% group-level-null patched output.
%
% Run this after running:
%   1) CARE_MVGC_FT_4ROI_Run
%   2) CARE_MVGC_FT_4ROI_Run_groupNull
%
% Expected folders under the current working directory:
%   MVGC_OUT_FT4ROI
%   MVGC_OUT_FT4ROI_groupNull
%
% Output:
%   MVGC_OUT_FT4ROI_compare/Permutation_Comparison_Report.csv
% ------------------------------------------------------------
clc;

baseDir = pwd;
oldDir = fullfile(baseDir, 'MVGC_OUT_FT4ROI');
newDir = fullfile(baseDir, 'MVGC_OUT_FT4ROI_groupNull');
outDir = fullfile(baseDir, 'MVGC_OUT_FT4ROI_compare');
if ~exist(outDir, 'dir'); mkdir(outDir); end

oldSummaryPath = fullfile(oldDir, 'GC_null_summary_FT.csv');
newSummaryPath = fullfile(newDir, 'GC_null_summary_FT.csv');
newGroupPath = fullfile(newDir, 'GC_null_groupStats_FT.csv');

assert(exist(oldSummaryPath, 'file') == 2, 'Missing old summary: %s', oldSummaryPath);
assert(exist(newSummaryPath, 'file') == 2, 'Missing new summary: %s', newSummaryPath);
assert(exist(newGroupPath, 'file') == 2, 'Missing new group stats: %s', newGroupPath);

oldS = readtable(oldSummaryPath, 'TextType', 'string');
newS = readtable(newSummaryPath, 'TextType', 'string');
newG = readtable(newGroupPath, 'TextType', 'string');

rows = {};
rows(end+1,:) = {'real_mean_old', getnum(oldS, 'real_mean'), ''}; %#ok<AGROW>
rows(end+1,:) = {'real_mean_new', getnum(newS, 'real_mean'), ''}; %#ok<AGROW>
rows(end+1,:) = {'real_sd_old', getnum(oldS, 'real_sd'), ''}; %#ok<AGROW>
rows(end+1,:) = {'real_sd_new', getnum(newS, 'real_sd'), ''}; %#ok<AGROW>

rows(end+1,:) = {'old_pseudo_p_original_oneSided', getnum(oldS, 'p_empirical_pseudo_oneSided'), ...
    'Original script compared real group mean against unaggregated pseudo-dyad values.'}; %#ok<AGROW>
rows(end+1,:) = {'new_pseudo_p_upper_realGreater', getnum(newS, 'p_pseudo_upper_realGreater'), ...
    'Group-level null test: probability null group mean >= real group mean.'}; %#ok<AGROW>
rows(end+1,:) = {'new_pseudo_p_lower_realLower', getnum(newS, 'p_pseudo_lower_realLower'), ...
    'Group-level null test: probability null group mean <= real group mean.'}; %#ok<AGROW>
rows(end+1,:) = {'new_pseudo_p_twoSided', getnum(newS, 'p_pseudo_twoSided'), ...
    'Two-sided empirical p-value with add-one correction.'}; %#ok<AGROW>

rows(end+1,:) = {'old_block_p_original_oneSided', getnum(oldS, 'p_empirical_block_oneSided'), ...
    'Original script compared real group mean against unaggregated block-null values.'}; %#ok<AGROW>
rows(end+1,:) = {'new_block_p_upper_realGreater', getnum(newS, 'p_block_upper_realGreater'), ...
    'Group-level null test: probability null group mean >= real group mean.'}; %#ok<AGROW>
rows(end+1,:) = {'new_block_p_lower_realLower', getnum(newS, 'p_block_lower_realLower'), ...
    'Group-level null test: probability null group mean <= real group mean.'}; %#ok<AGROW>
rows(end+1,:) = {'new_block_p_twoSided', getnum(newS, 'p_block_twoSided'), ...
    'Two-sided empirical p-value with add-one correction.'}; %#ok<AGROW>

rows(end+1,:) = {'new_pseudo_group_mean', getnum(newS, 'pseudo_group_mean'), ''}; %#ok<AGROW>
rows(end+1,:) = {'new_pseudo_group_sd', getnum(newS, 'pseudo_group_sd'), ''}; %#ok<AGROW>
rows(end+1,:) = {'new_block_group_mean', getnum(newS, 'block_group_mean'), ''}; %#ok<AGROW>
rows(end+1,:) = {'new_block_group_sd', getnum(newS, 'block_group_sd'), ''}; %#ok<AGROW>

if any(strcmp(newG.Properties.VariableNames, 'pseudo_group_mean'))
    pseudoVals = newG.pseudo_group_mean(isfinite(newG.pseudo_group_mean));
    rows(end+1,:) = {'new_pseudo_group_min', min_or_nan(pseudoVals), ''}; %#ok<AGROW>
    rows(end+1,:) = {'new_pseudo_group_max', max_or_nan(pseudoVals), ''}; %#ok<AGROW>
end
if any(strcmp(newG.Properties.VariableNames, 'block_group_mean'))
    blockVals = newG.block_group_mean(isfinite(newG.block_group_mean));
    rows(end+1,:) = {'new_block_group_min', min_or_nan(blockVals), ''}; %#ok<AGROW>
    rows(end+1,:) = {'new_block_group_max', max_or_nan(blockVals), ''}; %#ok<AGROW>
end

report = cell2table(rows, 'VariableNames', {'Metric','Value','Interpretation'});
outPath = fullfile(outDir, 'Permutation_Comparison_Report.csv');
writetable(report, outPath);

fprintf('\nComparison report saved to:\n%s\n', outPath);
disp(report);
end

function val = getnum(T, name)
if any(strcmp(T.Properties.VariableNames, name))
    x = T.(name);
    if isempty(x)
        val = NaN;
    else
        val = x(1);
    end
else
    val = NaN;
end
end

function val = min_or_nan(x)
if isempty(x)
    val = NaN;
else
    val = min(x);
end
end

function val = max_or_nan(x)
if isempty(x)
    val = NaN;
else
    val = max(x);
end
end
