# ======================================================================================
# STUDY 1 — PARENT-LED DEVELOPMENTAL CALIBRATION
# Age-covariate version: child age is included in mediator and outcome models.
# Core pathway: RIFL -> RJA -> Task
# Final analytic population: Study 1 N90
# ======================================================================================

while (sink.number() > 0) sink()

# ======================================================================================
# SECTION 1 — Setup
# ======================================================================================

out_dir <- "~/Desktop/Preprocessing/Study123/Study1_ParentLed_Calibration_N90_AgeCovariate"
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

data_file <- "/Users/janet/Desktop/Preprocessing/Study123_PopulationScreening/Study1_2_3_Screened_Populations/df_study1_CalibratingLearning_N90.csv"
pkgs <- c(
  "tidyverse", "lavaan", "psych", "flextable", "officer",
  "broom", "semPlot", "patchwork", "glue", "progress"
)

new_pkgs <- pkgs[!(pkgs %in% installed.packages()[, "Package"])]
if(length(new_pkgs)) install.packages(new_pkgs)
invisible(lapply(pkgs, library, character.only = TRUE))

theme_set(theme_classic(base_size = 14))

COL_RIFL <- "#F28E8C"
COL_RJA  <- "#2DB84D"
COL_TASK <- "#6A9CF7"

safe_num <- function(x) suppressWarnings(as.numeric(x))

fmt_p <- function(p){
  p <- suppressWarnings(as.numeric(p))
  if(is.na(p)) return("p = NA")
  if(p < .001) return("p < .001")
  paste0("p = ", sprintf("%.3f", p))
}

fmt_p_apa <- function(p){
  p <- suppressWarnings(as.numeric(p))
  dplyr::case_when(
    is.na(p) ~ NA_character_,
    p < .001 ~ "< .001",
    TRUE ~ sprintf("%.3f", p)
  )
}

sig_flag <- function(p){
  p <- suppressWarnings(as.numeric(p))
  dplyr::case_when(
    is.na(p) ~ "NA",
    p < .001 ~ "***",
    p < .01 ~ "**",
    p < .05 ~ "*",
    TRUE ~ "ns"
  )
}

apa_m_sd <- function(x){
  x <- safe_num(x)
  if(all(is.na(x))) return(NA_character_)
  sprintf("%.2f (%.2f)", mean(x, na.rm = TRUE), sd(x, na.rm = TRUE))
}

apa_range <- function(x){
  x <- safe_num(x)
  if(all(is.na(x))) return(NA_character_)
  sprintf("%.2f–%.2f", min(x, na.rm = TRUE), max(x, na.rm = TRUE))
}

round_df <- function(df, digits = 3){
  df %>% dplyr::mutate(dplyr::across(where(is.numeric), ~ round(.x, digits)))
}

get_col_safe <- function(data, candidates){
  found <- candidates[candidates %in% names(data)]
  if(length(found) == 0) return(rep(NA, nrow(data)))
  data[[found[1]]]
}

get_sex_safe <- function(data){
  if("Gender" %in% names(data)){
    x <- as.character(data$Gender)
  } else if("Child_Sex" %in% names(data)){
    x <- as.character(data$Child_Sex)
  } else if("Sex" %in% names(data)){
    x <- as.character(data$Sex)
  } else {
    return(rep(NA_character_, nrow(data)))
  }
  
  dplyr::case_when(
    x %in% c("0", "Female", "female", "F", "f", "Girl", "girl") ~ "Female",
    x %in% c("1", "Male", "male", "M", "m", "Boy", "boy") ~ "Male",
    TRUE ~ x
  )
}

summarise_model_n <- function(df, vars, model_name){
  tibble::tibble(
    Model = model_name,
    Variables = paste(vars, collapse = ", "),
    N_complete = sum(complete.cases(df[, vars]))
  )
}

extract_path_row <- function(params_tbl, lhs_name, rhs_name){
  params_tbl %>%
    dplyr::filter(lhs == lhs_name, rhs == rhs_name, op == "~") %>%
    dplyr::slice(1)
}

extract_label_row <- function(params_tbl, label_name){
  params_tbl %>%
    dplyr::filter(label == label_name) %>%
    dplyr::slice(1)
}

save_text_summary <- function(obj, path){
  writeLines(capture.output(obj), con = path)
}

# ======================================================================================
# SECTION 2 — Mediation function
# ======================================================================================

run_parent_mediation <- function(data, out_prefix, nboot = 5000){
  
  stopifnot(all(c("RIFL_Z", "RJA_Z", "Task_Z", "ChildAge_Z") %in% names(data)))
  
  model_med <- '
    RJA_Z  ~ a * RIFL_Z + age_m * ChildAge_Z
    Task_Z ~ b * RJA_Z + cprime * RIFL_Z + age_y * ChildAge_Z

    indirect := a * b
    total := indirect + cprime
  '
  
  fit <- lavaan::sem(
    model_med,
    data = data,
    se = "bootstrap",
    bootstrap = nboot,
    estimator = "ML"
  )
  
  params <- lavaan::parameterEstimates(
    fit,
    standardized = TRUE,
    ci = TRUE,
    boot.ci.type = "perc"
  ) %>%
    tibble::as_tibble()
  
  fit_measures <- lavaan::fitMeasures(
    fit,
    c("chisq", "df", "pvalue", "cfi", "tli", "rmsea", "srmr")
  )
  
  fit_tbl <- tibble::tibble(
    chisq = fit_measures["chisq"],
    df = fit_measures["df"],
    pvalue = fit_measures["pvalue"],
    CFI = fit_measures["cfi"],
    TLI = fit_measures["tli"],
    RMSEA = fit_measures["rmsea"],
    SRMR = fit_measures["srmr"]
  )
  
  key_tbl <- dplyr::bind_rows(
    {
      a <- extract_path_row(params, "RJA_Z", "RIFL_Z")
      tibble::tibble(
        Effect = "A_path_RIFL_to_RJA",
        est = a$est, se = a$se, z = a$z, pvalue = a$pvalue,
        ci.lower = a$ci.lower, ci.upper = a$ci.upper, std.all = a$std.all
      )
    },
    {
      b <- extract_path_row(params, "Task_Z", "RJA_Z")
      tibble::tibble(
        Effect = "B_path_RJA_to_Task_controlled_RIFL_age",
        est = b$est, se = b$se, z = b$z, pvalue = b$pvalue,
        ci.lower = b$ci.lower, ci.upper = b$ci.upper, std.all = b$std.all
      )
    },
    {
      cpr <- extract_path_row(params, "Task_Z", "RIFL_Z")
      tibble::tibble(
        Effect = "Direct_RIFL_to_Task_cprime",
        est = cpr$est, se = cpr$se, z = cpr$z, pvalue = cpr$pvalue,
        ci.lower = cpr$ci.lower, ci.upper = cpr$ci.upper, std.all = cpr$std.all
      )
    },
    {
      age_m <- extract_path_row(params, "RJA_Z", "ChildAge_Z")
      tibble::tibble(
        Effect = "Covariate_ChildAge_to_RJA",
        est = age_m$est, se = age_m$se, z = age_m$z, pvalue = age_m$pvalue,
        ci.lower = age_m$ci.lower, ci.upper = age_m$ci.upper, std.all = age_m$std.all
      )
    },
    {
      age_y <- extract_path_row(params, "Task_Z", "ChildAge_Z")
      tibble::tibble(
        Effect = "Covariate_ChildAge_to_Task",
        est = age_y$est, se = age_y$se, z = age_y$z, pvalue = age_y$pvalue,
        ci.lower = age_y$ci.lower, ci.upper = age_y$ci.upper, std.all = age_y$std.all
      )
    },
    {
      ind <- extract_label_row(params, "indirect")
      tibble::tibble(
        Effect = "Indirect_RIFL_to_RJA_to_Task",
        est = ind$est, se = ind$se, z = ind$z, pvalue = ind$pvalue,
        ci.lower = ind$ci.lower, ci.upper = ind$ci.upper, std.all = ind$std.all
      )
    },
    {
      tot <- extract_label_row(params, "total")
      tibble::tibble(
        Effect = "Total",
        est = tot$est, se = tot$se, z = tot$z, pvalue = tot$pvalue,
        ci.lower = tot$ci.lower, ci.upper = tot$ci.upper, std.all = tot$std.all
      )
    }
  ) %>%
    dplyr::mutate(
      N = nrow(data),
      Significance = sapply(pvalue, sig_flag)
    )
  
  readr::write_csv(params, paste0(out_prefix, "_Mediation_Params.csv"))
  readr::write_csv(fit_tbl, paste0(out_prefix, "_Mediation_FitIndices.csv"))
  readr::write_csv(key_tbl, paste0(out_prefix, "_Mediation_KeyResults.csv"))
  saveRDS(fit, paste0(out_prefix, "_Mediation_Fit.rds"))
  save_text_summary(
    summary(fit, fit.measures = TRUE, standardized = TRUE, rsquare = TRUE),
    paste0(out_prefix, "_Mediation_Summary.txt")
  )
  
  list(
    fit = fit,
    params = params,
    fit_tbl = fit_tbl,
    key_tbl = key_tbl
  )
}

# ======================================================================================
# SECTION 3 — Sliding-window function
# ======================================================================================

run_quantile_jn_sliding <- function(
    data,
    out_dir,
    prefix = "Study1_N90",
    width_q = 0.35,
    step_q = 0.05,
    min_n_in_win = 22,
    nboot = 2000,
    estimator = "ML",
    boot_ci_type = "perc",
    overlap = TRUE,
    n_bins = 6,
    fit_for_pathdiag = NULL,
    params_full = NULL
){
  
  stopifnot(all(c("RIFL_Z", "RJA_Z", "Task_Z", "ChildAge_Z") %in% names(data)))
  dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
  
  model_med <- '
    RJA_Z  ~ a * RIFL_Z + age_m * ChildAge_Z
    Task_Z ~ b * RJA_Z + cprime * RIFL_Z + age_y * ChildAge_Z

    indirect := a * b
    total := indirect + cprime
  '
  
  if(overlap){
    centers_q <- seq(width_q / 2, 1 - width_q / 2, by = step_q)
  } else {
    probs <- seq(0, 1, length.out = n_bins + 1)
    centers_q <- (probs[-1] + probs[-length(probs)]) / 2
    width_q <- 1 / n_bins
  }
  
  win_results <- tibble::tibble(
    center_q = numeric(),
    center_RJA = numeric(),
    lo_q = numeric(),
    hi_q = numeric(),
    lo_RJA = numeric(),
    hi_RJA = numeric(),
    n = integer(),
    indirect = numeric(),
    se = numeric(),
    pvalue = numeric(),
    ci.lower = numeric(),
    ci.upper = numeric(),
    converged = logical(),
    notes = character()
  )
  
  pb <- progress::progress_bar$new(
    total = length(centers_q),
    format = "[:bar] :current/:total (:percent) eta: :eta"
  )
  
  for(cq in centers_q){
    
    pb$tick()
    
    lo_q <- max(0, cq - width_q / 2)
    hi_q <- min(1, cq + width_q / 2)
    
    rja_lo <- stats::quantile(data$RJA_Z, probs = lo_q, na.rm = TRUE)
    rja_hi <- stats::quantile(data$RJA_Z, probs = hi_q, na.rm = TRUE)
    
    df_win <- data %>%
      dplyr::filter(RJA_Z >= rja_lo, RJA_Z <= rja_hi)
    
    nwin <- nrow(df_win)
    
    if(nwin < min_n_in_win){
      win_results <- win_results %>%
        dplyr::add_row(
          center_q = cq,
          center_RJA = NA_real_,
          lo_q = lo_q,
          hi_q = hi_q,
          lo_RJA = rja_lo,
          hi_RJA = rja_hi,
          n = nwin,
          indirect = NA_real_,
          se = NA_real_,
          pvalue = NA_real_,
          ci.lower = NA_real_,
          ci.upper = NA_real_,
          converged = FALSE,
          notes = "too few obs"
        )
      next
    }
    
    fit_win <- tryCatch({
      lavaan::sem(
        model_med,
        data = df_win,
        estimator = estimator,
        se = "bootstrap",
        bootstrap = nboot
      )
    }, error = function(e) NULL)
    
    if(is.null(fit_win) || !lavaan::inspect(fit_win, "converged")){
      win_results <- win_results %>%
        dplyr::add_row(
          center_q = cq,
          center_RJA = stats::median(df_win$RJA_Z, na.rm = TRUE),
          lo_q = lo_q,
          hi_q = hi_q,
          lo_RJA = rja_lo,
          hi_RJA = rja_hi,
          n = nwin,
          indirect = NA_real_,
          se = NA_real_,
          pvalue = NA_real_,
          ci.lower = NA_real_,
          ci.upper = NA_real_,
          converged = FALSE,
          notes = "fit error or not converged"
        )
      next
    }
    
    params_win <- tryCatch({
      lavaan::parameterEstimates(
        fit_win,
        standardized = TRUE,
        ci = TRUE,
        boot.ci.type = boot_ci_type
      )
    }, error = function(e) NULL)
    
    if(is.null(params_win)){
      win_results <- win_results %>%
        dplyr::add_row(
          center_q = cq,
          center_RJA = stats::median(df_win$RJA_Z, na.rm = TRUE),
          lo_q = lo_q,
          hi_q = hi_q,
          lo_RJA = rja_lo,
          hi_RJA = rja_hi,
          n = nwin,
          indirect = NA_real_,
          se = NA_real_,
          pvalue = NA_real_,
          ci.lower = NA_real_,
          ci.upper = NA_real_,
          converged = TRUE,
          notes = "param extract failed"
        )
      next
    }
    
    ind_row <- params_win %>%
      dplyr::filter(label == "indirect") %>%
      dplyr::slice(1)
    
    if(nrow(ind_row) == 0){
      win_results <- win_results %>%
        dplyr::add_row(
          center_q = cq,
          center_RJA = stats::median(df_win$RJA_Z, na.rm = TRUE),
          lo_q = lo_q,
          hi_q = hi_q,
          lo_RJA = rja_lo,
          hi_RJA = rja_hi,
          n = nwin,
          indirect = NA_real_,
          se = NA_real_,
          pvalue = NA_real_,
          ci.lower = NA_real_,
          ci.upper = NA_real_,
          converged = TRUE,
          notes = "no indirect row"
        )
      next
    }
    
    win_results <- win_results %>%
      dplyr::add_row(
        center_q = cq,
        center_RJA = stats::median(df_win$RJA_Z, na.rm = TRUE),
        lo_q = lo_q,
        hi_q = hi_q,
        lo_RJA = rja_lo,
        hi_RJA = rja_hi,
        n = nwin,
        indirect = ind_row$est,
        se = ind_row$se,
        pvalue = ind_row$pvalue,
        ci.lower = ind_row$ci.lower,
        ci.upper = ind_row$ci.upper,
        converged = TRUE,
        notes = "ok"
      )
  }
  
  win_results <- win_results %>%
    dplyr::mutate(
      sig = !is.na(ci.lower) & !is.na(ci.upper) & (ci.lower > 0 | ci.upper < 0)
    )
  
  sig_windows <- win_results %>%
    dplyr::filter(sig)
  
  readr::write_csv(win_results, file.path(out_dir, "quantile_JN_window_results.csv"))
  readr::write_csv(sig_windows, file.path(out_dir, "quantile_JN_sig_windows.csv"))
  
  sig_summary <- if(nrow(sig_windows) > 0){
    tibble::tibble(
      n_sig_windows = nrow(sig_windows),
      min_center_q = min(sig_windows$center_q, na.rm = TRUE),
      max_center_q = max(sig_windows$center_q, na.rm = TRUE),
      min_center_RJA = min(sig_windows$center_RJA, na.rm = TRUE),
      max_center_RJA = max(sig_windows$center_RJA, na.rm = TRUE),
      min_lo_q = min(sig_windows$lo_q, na.rm = TRUE),
      max_hi_q = max(sig_windows$hi_q, na.rm = TRUE),
      min_lo_RJA = min(sig_windows$lo_RJA, na.rm = TRUE),
      max_hi_RJA = max(sig_windows$hi_RJA, na.rm = TRUE),
      peak_indirect = sig_windows$indirect[which.max(abs(sig_windows$indirect))],
      peak_center_RJA = sig_windows$center_RJA[which.max(abs(sig_windows$indirect))]
    )
  } else {
    tibble::tibble(
      n_sig_windows = 0,
      min_center_q = NA_real_,
      max_center_q = NA_real_,
      min_center_RJA = NA_real_,
      max_center_RJA = NA_real_,
      min_lo_q = NA_real_,
      max_hi_q = NA_real_,
      min_lo_RJA = NA_real_,
      max_hi_RJA = NA_real_,
      peak_indirect = NA_real_,
      peak_center_RJA = NA_real_
    )
  } %>%
    dplyr::mutate(
      width_q = width_q,
      step_q = step_q,
      min_n_in_win = min_n_in_win,
      nboot = nboot,
      overlap = overlap,
      n_bins = n_bins,
      center_definition = "Median RJA_Z within each quantile-defined window",
      significance_rule = "95% bootstrap CI excludes zero",
      window_definition = "Quantile-defined sliding windows on RJA_Z"
    )
  
  readr::write_csv(
    sig_summary,
    file.path(out_dir, paste0(prefix, "_SlidingWindow_SigSummary.csv"))
  )
  
  p_jn <- ggplot2::ggplot(
    win_results %>% dplyr::filter(!is.na(center_RJA)),
    ggplot2::aes(x = center_RJA, y = indirect)
  ) +
    ggplot2::geom_ribbon(
      ggplot2::aes(ymin = ci.lower, ymax = ci.upper),
      fill = "grey80",
      alpha = .7
    ) +
    ggplot2::geom_line(linewidth = 1) +
    ggplot2::geom_point(ggplot2::aes(size = n, color = sig)) +
    ggplot2::scale_color_manual(values = c("FALSE" = "black", "TRUE" = "#D73027"), guide = "none") +
    ggplot2::scale_size_continuous(name = "N (window)", range = c(2, 6)) +
    ggplot2::geom_hline(yintercept = 0, linetype = "dashed") +
    ggplot2::labs(
      title = "Sliding-window indirect effect: RIFL → RJA → Task",
      subtitle = glue::glue("Quantile width = {width_q}; step = {step_q}; min_N = {min_n_in_win}; nboot = {nboot}"),
      x = "RJA (z): window median",
      y = "Indirect effect (a × b)"
    ) +
    ggplot2::theme_classic(base_size = 14)
  
  ggplot2::ggsave(
    file.path(out_dir, "06_JN_style_sliding_window_indirects.png"),
    p_jn,
    width = 9,
    height = 5,
    dpi = 320,
    bg = "white"
  )
  
  ggplot2::ggsave(
    file.path(out_dir, paste0(prefix, "_SlidingWindow_Plot.png")),
    p_jn,
    width = 9,
    height = 5,
    dpi = 320,
    bg = "white"
  )
  
  if(!is.null(fit_for_pathdiag)){
    png(
      file.path(out_dir, "09_mediation_path_diagram.png"),
      width = 1200,
      height = 800,
      res = 150
    )
    semPlot::semPaths(
      fit_for_pathdiag,
      whatLabels = "std",
      style = "ram",
      edge.label.cex = 1.2,
      intercepts = FALSE
    )
    dev.off()
  }
  
  list(
    all = win_results,
    sig = sig_windows,
    sig_summary = sig_summary,
    plot = p_jn
  )
}

# ======================================================================================
# SECTION 4 — Load and prepare N90 data
# ======================================================================================

cat("\n📌 SECTION 4 — Loading Study 1 N90 data...\n")

df_raw <- readr::read_csv(data_file, show_col_types = FALSE)

df_clean <- df_raw %>%
  dplyr::mutate(
    UID = as.character(UID),
    
    RIFL = safe_num(RIFL),
    Obj_RJA = safe_num(Obj_RJA),
    ChildAge = safe_num(get_col_safe(., c("Child_Age_Year", "Child_Age", "Age_Year", "Age"))),
    
    Task_Peg_Z = if("Task_Peg" %in% names(.)) as.numeric(scale(Task_Peg)) else NA_real_,
    Task_Dpl_Z = if("Task_Dpl" %in% names(.)) as.numeric(scale(Task_Dpl)) else NA_real_,
    
    TaskPerformance = dplyr::case_when(
      "TaskPerformance" %in% names(.) ~ safe_num(TaskPerformance),
      TRUE ~ dplyr::coalesce(Task_Dpl_Z, Task_Peg_Z)
    ),
    
    RIFL_Z = as.numeric(scale(RIFL)),
    RJA_Z = as.numeric(scale(Obj_RJA)),
    Task_Z = as.numeric(scale(TaskPerformance)),
    ChildAge_Z = as.numeric(scale(ChildAge)),
    
    Gender = get_sex_safe(.)
  )

df_parent_med <- df_clean %>%
  tidyr::drop_na(RIFL_Z, RJA_Z, Task_Z, ChildAge_Z)

readr::write_csv(
  df_parent_med,
  file.path(out_dir, "00_Study1_N90_ModelReady.csv")
)

cat("Model-ready N =", nrow(df_parent_med), "\n")

# ======================================================================================
# SECTION 5 — Descriptives and correlations
# ======================================================================================

cat("\n📌 SECTION 5 — Running descriptives...\n")

desc_dir <- file.path(out_dir, "Descriptives")
dir.create(desc_dir, recursive = TRUE, showWarnings = FALSE)

df_demo <- df_parent_med %>%
  dplyr::mutate(
    MotherAge = safe_num(get_col_safe(., c("Mother_Age_Year", "Maternal_Age", "M_Age", "MotherAge"))),
    MotherEdu = safe_num(get_col_safe(., c("Mother_Edu", "Maternal_Edu", "Mother_Education", "MotherEdu"))),
    Income = safe_num(get_col_safe(., c("Family_Income", "Income", "FamilyIncome", "Household_Income"))),
    Sex = get_sex_safe(.)
  )

demo_var_mapping <- tibble::tibble(
  Target = c("Child age", "Mother age", "Mother education", "Family income", "Sex"),
  Used_column = c(
    names(df_parent_med)[names(df_parent_med) %in% c("Child_Age_Year", "Child_Age", "Age_Year", "Age")][1],
    names(df_parent_med)[names(df_parent_med) %in% c("Mother_Age", "Maternal_Age", "M_Age", "MotherAge")][1],
    names(df_parent_med)[names(df_parent_med) %in% c("Mother_Edu", "Maternal_Edu", "Mother_Education", "MotherEdu")][1],
    names(df_parent_med)[names(df_parent_med) %in% c("AnnualFamilyIncome", "Income", "FamilyIncome", "Household_Income")][1],
    names(df_parent_med)[names(df_parent_med) %in% c("Gender", "Child_Sex", "Sex")][1]
  )
)

readr::write_csv(
  demo_var_mapping,
  file.path(desc_dir, "00_DemographicVariableMapping.csv")
)

n_female <- sum(df_demo$Sex == "Female", na.rm = TRUE)
n_male <- sum(df_demo$Sex == "Male", na.rm = TRUE)
n_sex <- sum(df_demo$Sex %in% c("Female", "Male"), na.rm = TRUE)

sex_pct <- function(n){
  if(n_sex == 0) return(NA_character_)
  paste0(n, " (", round(100 * n / n_sex, 1), "%)")
}

demo_tbl <- tibble::tibble(
  Variable = c(
    "Child age (years)",
    "Child sex: female",
    "Child sex: male",
    "Maternal age",
    "Maternal education",
    "Family income"
  ),
  N = c(
    sum(!is.na(df_demo$ChildAge)),
    n_sex,
    n_sex,
    sum(!is.na(df_demo$MotherAge)),
    sum(!is.na(df_demo$MotherEdu)),
    sum(!is.na(df_demo$Income))
  ),
  `M (SD) / n (%)` = c(
    apa_m_sd(df_demo$ChildAge),
    sex_pct(n_female),
    sex_pct(n_male),
    apa_m_sd(df_demo$MotherAge),
    apa_m_sd(df_demo$MotherEdu),
    apa_m_sd(df_demo$Income)
  ),
  Range = c(
    apa_range(df_demo$ChildAge),
    "",
    "",
    apa_range(df_demo$MotherAge),
    apa_range(df_demo$MotherEdu),
    apa_range(df_demo$Income)
  )
)

readr::write_csv(
  demo_tbl,
  file.path(desc_dir, "01_APA_ParticipantCharacteristics.csv")
)

core_desc_tbl <- tibble::tibble(
  Variable = c("RIFL", "RJA", "Task performance"),
  N = c(
    sum(!is.na(df_parent_med$RIFL)),
    sum(!is.na(df_parent_med$Obj_RJA)),
    sum(!is.na(df_parent_med$TaskPerformance))
  ),
  M = c(
    mean(df_parent_med$RIFL, na.rm = TRUE),
    mean(df_parent_med$Obj_RJA, na.rm = TRUE),
    mean(df_parent_med$TaskPerformance, na.rm = TRUE)
  ),
  SD = c(
    sd(df_parent_med$RIFL, na.rm = TRUE),
    sd(df_parent_med$Obj_RJA, na.rm = TRUE),
    sd(df_parent_med$TaskPerformance, na.rm = TRUE)
  ),
  Min = c(
    min(df_parent_med$RIFL, na.rm = TRUE),
    min(df_parent_med$Obj_RJA, na.rm = TRUE),
    min(df_parent_med$TaskPerformance, na.rm = TRUE)
  ),
  Max = c(
    max(df_parent_med$RIFL, na.rm = TRUE),
    max(df_parent_med$Obj_RJA, na.rm = TRUE),
    max(df_parent_med$TaskPerformance, na.rm = TRUE)
  ),
  Skew = c(
    psych::skew(df_parent_med$RIFL, na.rm = TRUE),
    psych::skew(df_parent_med$Obj_RJA, na.rm = TRUE),
    psych::skew(df_parent_med$TaskPerformance, na.rm = TRUE)
  ),
  Kurtosis = c(
    psych::kurtosi(df_parent_med$RIFL, na.rm = TRUE),
    psych::kurtosi(df_parent_med$Obj_RJA, na.rm = TRUE),
    psych::kurtosi(df_parent_med$TaskPerformance, na.rm = TRUE)
  )
) %>%
  round_df(3)

readr::write_csv(
  core_desc_tbl,
  file.path(desc_dir, "02_APA_CoreVariable_Descriptives.csv")
)

cor_dat <- df_parent_med %>%
  dplyr::transmute(
    RIFL = RIFL_Z,
    RJA = RJA_Z,
    Task = Task_Z
  ) %>%
  tidyr::drop_na()

cor_test <- psych::corr.test(cor_dat, adjust = "none")

r_mat <- cor_test$r
p_mat <- cor_test$p
n_mat <- cor_test$n

cor_long <- expand.grid(
  Var1 = rownames(r_mat),
  Var2 = colnames(r_mat),
  stringsAsFactors = FALSE
) %>%
  dplyr::mutate(
    r = as.vector(r_mat),
    p = as.vector(p_mat),
    n = as.vector(n_mat),
    r_APA = paste0(sprintf("%.2f", r), sig_flag(p)),
    p_APA = fmt_p_apa(p)
  ) %>%
  dplyr::filter(Var1 != Var2)

readr::write_csv(
  cor_long,
  file.path(desc_dir, "03_APA_CoreVariable_Correlations_Long.csv")
)

get_r_apa <- function(v1, v2){
  out <- cor_long %>%
    dplyr::filter(Var1 == v1, Var2 == v2) %>%
    dplyr::slice(1) %>%
    dplyr::pull(r_APA)
  if(length(out) == 0) "" else out
}

cor_apa_tbl <- tibble::tibble(
  Variable = c("1. RIFL", "2. RJA", "3. Task performance"),
  M = round(c(mean(cor_dat$RIFL), mean(cor_dat$RJA), mean(cor_dat$Task)), 2),
  SD = round(c(sd(cor_dat$RIFL), sd(cor_dat$RJA), sd(cor_dat$Task)), 2),
  `1` = c("—", get_r_apa("RJA", "RIFL"), get_r_apa("Task", "RIFL")),
  `2` = c("", "—", get_r_apa("Task", "RJA")),
  `3` = c("", "", "—")
)

readr::write_csv(
  cor_apa_tbl,
  file.path(desc_dir, "04_APA_CoreVariable_CorrelationTable.csv")
)

# ======================================================================================
# SECTION 6 — Raincloud plots
# ======================================================================================

cat("\n📌 SECTION 6 — Creating raincloud plots...\n")

make_single_raincloud <- function(data, var, label, ylab, outfile, fill_col){
  
  plot_dat <- data %>%
    dplyr::select(UID, score = dplyr::all_of(var)) %>%
    dplyr::mutate(
      score = safe_num(score),
      x_point = 1.18,
      x_box = 0.95,
      x_edge = 0.62
    ) %>%
    dplyr::filter(is.finite(score))
  
  if(nrow(plot_dat) < 6) return(NULL)
  
  data_max <- max(plot_dat$score, na.rm = TRUE)
  data_min <- min(plot_dat$score, na.rm = TRUE)
  data_range <- data_max - data_min
  if(!is.finite(data_range) || data_range == 0) data_range <- 1
  
  score_min <- floor(data_min)
  plot_y_max <- data_max + 0.10 * data_range
  
  sum_box <- plot_dat %>%
    dplyr::summarise(
      q1 = quantile(score, .25, na.rm = TRUE),
      q3 = quantile(score, .75, na.rm = TRUE),
      med = median(score, na.rm = TRUE),
      iqr = IQR(score, na.rm = TRUE),
      lower_fence = q1 - 1.5 * iqr,
      upper_fence = q3 + 1.5 * iqr,
      ymin = min(score[score >= lower_fence], na.rm = TRUE),
      ymax = max(score[score <= upper_fence], na.rm = TRUE)
    ) %>%
    dplyr::mutate(
      x_box = 0.95,
      xmin = x_box - .07,
      xmax = x_box + .07,
      cap_xmin = x_box - .05,
      cap_xmax = x_box + .05
    )
  
  dens <- stats::density(
    plot_dat$score,
    na.rm = TRUE,
    adjust = .75,
    from = min(plot_dat$score, na.rm = TRUE),
    to = max(plot_dat$score, na.rm = TRUE)
  )
  
  dens_scaled <- dens$y / max(dens$y) * .28
  edge <- unique(plot_dat$x_edge)[1]
  
  violin_poly <- dplyr::bind_rows(
    tibble::tibble(x = edge, y = min(dens$x, na.rm = TRUE)),
    tibble::tibble(x = edge - dens_scaled, y = dens$x),
    tibble::tibble(x = edge, y = max(dens$x, na.rm = TRUE))
  )
  
  p <- ggplot2::ggplot() +
    ggplot2::geom_polygon(
      data = violin_poly,
      ggplot2::aes(x = x, y = y),
      fill = fill_col,
      alpha = .80,
      colour = NA
    ) +
    ggplot2::geom_point(
      data = plot_dat,
      ggplot2::aes(x = x_point, y = score),
      position = ggplot2::position_jitter(width = .04, height = 0),
      size = 2.3,
      alpha = .70,
      colour = fill_col
    ) +
    ggplot2::geom_segment(data = sum_box, ggplot2::aes(x = x_box, xend = x_box, y = ymin, yend = ymax), colour = "black", linewidth = .75) +
    ggplot2::geom_segment(data = sum_box, ggplot2::aes(x = cap_xmin, xend = cap_xmax, y = ymin, yend = ymin), colour = "black", linewidth = .75) +
    ggplot2::geom_segment(data = sum_box, ggplot2::aes(x = cap_xmin, xend = cap_xmax, y = ymax, yend = ymax), colour = "black", linewidth = .75) +
    ggplot2::geom_rect(data = sum_box, ggplot2::aes(xmin = xmin, xmax = xmax, ymin = q1, ymax = q3), fill = fill_col, colour = "black", alpha = .65, linewidth = .75) +
    ggplot2::geom_segment(data = sum_box, ggplot2::aes(x = xmin, xend = xmax, y = med, yend = med), colour = "black", linewidth = .95) +
    ggplot2::stat_summary(data = plot_dat, ggplot2::aes(x = x_box, y = score), fun = mean, geom = "point", shape = 23, size = 3, fill = "white", colour = "black") +
    ggplot2::scale_x_continuous(breaks = 1, labels = label, limits = c(.25, 1.45), expand = c(0, 0)) +
    ggplot2::scale_y_continuous(limits = c(score_min, plot_y_max), expand = c(0.02, 0)) +
    ggplot2::labs(title = label, x = NULL, y = ylab) +
    ggplot2::theme_classic(base_size = 14) +
    ggplot2::theme(
      legend.position = "none",
      plot.title = ggplot2::element_text(face = "bold", hjust = .5),
      axis.title = ggplot2::element_text(face = "bold"),
      axis.text.x = ggplot2::element_text(face = "bold")
    )
  
  ggplot2::ggsave(
    file.path(desc_dir, outfile),
    p,
    width = 4.5,
    height = 5,
    dpi = 320,
    bg = "white"
  )
  
  p
}

p_rifl_rain <- make_single_raincloud(df_parent_med, "RIFL", "Caregiving Quality\n(RIFL)", "Observed score", "05_Raincloud_RIFL.png", COL_RIFL)
p_rja_rain <- make_single_raincloud(df_parent_med, "Obj_RJA", "Child RJA", "Observed frequency", "06_Raincloud_RJA.png", COL_RJA)
p_task_rain <- make_single_raincloud(df_parent_med, "TaskPerformance", "Task Performance", "Standardized task score", "07_Raincloud_Task.png", COL_TASK)

p_rain_combined <- p_rifl_rain + p_rja_rain + p_task_rain +
  patchwork::plot_annotation(title = "Study 1 Core Variable Distributions")

ggplot2::ggsave(
  file.path(desc_dir, "08_Raincloud_CoreVariables_Combined.png"),
  p_rain_combined,
  width = 12,
  height = 5,
  dpi = 320,
  bg = "white"
)

# ======================================================================================
# SECTION 7 — Bivariate association plots
# ======================================================================================

cat("\n📌 SECTION 7 — Creating bivariate plots...\n")

make_scatter_lm <- function(data, xvar, yvar, xlab, ylab, title, outfile, line_col){
  
  dat <- data %>%
    dplyr::transmute(
      x = safe_num(.data[[xvar]]),
      y = safe_num(.data[[yvar]])
    ) %>%
    tidyr::drop_na()
  
  fit <- lm(y ~ x, data = dat)
  rtest <- cor.test(dat$x, dat$y)
  
  ann <- paste0(
    "r = ", sprintf("%.2f", unname(rtest$estimate)),
    ", R² = ", sprintf("%.2f", summary(fit)$r.squared),
    ", ", fmt_p(rtest$p.value)
  )
  
  p <- ggplot2::ggplot(dat, ggplot2::aes(x = x, y = y)) +
    ggplot2::geom_point(alpha = .55, size = 2.4, colour = "grey35") +
    ggplot2::geom_smooth(method = "lm", se = TRUE, linewidth = 1.1, colour = line_col) +
    ggplot2::annotate("text", x = min(dat$x), y = max(dat$y), label = ann, hjust = 0, vjust = 1, size = 4.5) +
    ggplot2::theme_classic(base_size = 14) +
    ggplot2::labs(title = title, x = xlab, y = ylab) +
    ggplot2::theme(
      plot.title = ggplot2::element_text(face = "bold", hjust = .5),
      axis.title = ggplot2::element_text(face = "bold")
    )
  
  ggplot2::ggsave(
    file.path(desc_dir, outfile),
    p,
    width = 5.5,
    height = 4.5,
    dpi = 320,
    bg = "white"
  )
  
  p
}

p_rifl_rja <- make_scatter_lm(df_parent_med, "RIFL_Z", "RJA_Z", "RIFL (z)", "RJA (z)", "Caregiving Quality and Child RJA", "09_Scatter_RIFL_RJA.png", COL_RJA)
p_rja_task <- make_scatter_lm(df_parent_med, "RJA_Z", "Task_Z", "RJA (z)", "Task performance (z)", "Child RJA and Task Performance", "10_Scatter_RJA_Task.png", COL_TASK)
p_rifl_task <- make_scatter_lm(df_parent_med, "RIFL_Z", "Task_Z", "RIFL (z)", "Task performance (z)", "Caregiving Quality and Task Performance", "11_Scatter_RIFL_Task.png", COL_RIFL)

p_scatter_combined <- (p_rifl_rja | p_rja_task | p_rifl_task) +
  patchwork::plot_annotation(title = "Study 1 Core Bivariate Associations")

ggplot2::ggsave(
  file.path(desc_dir, "12_Scatter_CoreAssociations_Combined.png"),
  p_scatter_combined,
  width = 15,
  height = 4.8,
  dpi = 320,
  bg = "white"
)

# ======================================================================================
# SECTION 8 — Parent-led regression pathway: RIFL -> RJA -> Task
# ======================================================================================

cat("\n📌 SECTION 8 — Running parent-led regression models...\n")

reg_dir <- file.path(out_dir, "Regression_ParentLed")
dir.create(reg_dir, recursive = TRUE, showWarnings = FALSE)

run_lm_apa <- function(data, formula_txt, model_label){
  fit <- lm(as.formula(formula_txt), data = data)
  
  coef_tbl <- broom::tidy(fit, conf.int = TRUE) %>%
    mutate(
      Model = model_label,
      Formula = formula_txt,
      N = nrow(model.frame(fit)),
      p_APA = purrr::map_chr(p.value, fmt_p),
      Significance = purrr::map_chr(p.value, sig_flag)
    )
  
  fit_tbl <- broom::glance(fit) %>%
    mutate(
      Model = model_label,
      Formula = formula_txt,
      N = nrow(model.frame(fit)),
      p_APA = fmt_p(p.value)
    )
  
  list(fit = fit, coef = coef_tbl, fit_tbl = fit_tbl)
}

parent_reg_specs <- tibble::tribble(
  ~Model_Label, ~Formula,
  "Age-adjusted linear A-path: RIFL -> RJA", "RJA_Z ~ RIFL_Z + ChildAge_Z",
  "Age-adjusted linear B-path: RJA -> Task", "Task_Z ~ RJA_Z + ChildAge_Z",
  "Age-adjusted total/direct caregiving path: RIFL -> Task", "Task_Z ~ RIFL_Z + ChildAge_Z",
  "Age-adjusted controlled outcome model: Task ~ RIFL + RJA", "Task_Z ~ RIFL_Z + RJA_Z + ChildAge_Z"
)

parent_reg_results <- purrr::map2(
  parent_reg_specs$Formula,
  parent_reg_specs$Model_Label,
  ~ run_lm_apa(df_parent_med, .x, .y)
)

parent_reg_coef <- purrr::map_dfr(parent_reg_results, "coef")
parent_reg_fit <- purrr::map_dfr(parent_reg_results, "fit_tbl")

write_csv(round_df(parent_reg_coef, 3),
          file.path(reg_dir, "01_ParentLed_LinearRegression_Coefficients.csv"))

write_csv(round_df(parent_reg_fit, 3),
          file.path(reg_dir, "02_ParentLed_LinearRegression_ModelFit.csv"))

# ------------------------------------------------------------
# Nonlinear/piecewise helper
# ------------------------------------------------------------

fit_linear_quad_piece <- function(data, x, y, knot = NULL, label, covariates = "ChildAge_Z"){
  
  covariates <- covariates[covariates %in% names(data)]
  
  d <- data %>%
    dplyr::select(all_of(c(x, y, covariates))) %>%
    tidyr::drop_na()
  
  if(is.null(knot)) knot <- median(d[[x]], na.rm = TRUE)
  
  d <- d %>%
    mutate(
      x_raw = .data[[x]],
      y_raw = .data[[y]],
      x_sq = x_raw^2,
      x_post = pmax(0, x_raw - knot)
    )
  
  cov_txt <- if(length(covariates) > 0) paste(covariates, collapse = " + ") else NULL
  rhs1 <- paste(c("x_raw", cov_txt), collapse = " + ")
  rhs2 <- paste(c("x_raw", "x_sq", cov_txt), collapse = " + ")
  rhs3 <- paste(c("x_raw", "x_post", cov_txt), collapse = " + ")
  
  m1 <- lm(as.formula(paste("y_raw ~", rhs1)), data = d)
  m2 <- lm(as.formula(paste("y_raw ~", rhs2)), data = d)
  m3 <- lm(as.formula(paste("y_raw ~", rhs3)), data = d)
  
  fit_tbl <- bind_rows(
    broom::glance(m1) %>% mutate(Model = "Linear"),
    broom::glance(m2) %>% mutate(Model = "Quadratic"),
    broom::glance(m3) %>% mutate(Model = "Piecewise_1knot")
  ) %>%
    mutate(
      Path = label,
      X = x,
      Y = y,
      Covariates = ifelse(length(covariates) > 0, paste(covariates, collapse = ", "), "None"),
      N = nrow(d),
      Knot = ifelse(Model == "Piecewise_1knot", knot, NA_real_),
      p_APA = purrr::map_chr(p.value, fmt_p),
      Significance = purrr::map_chr(p.value, sig_flag)
    )
  
  coef_tbl <- bind_rows(
    broom::tidy(m1, conf.int = TRUE) %>% mutate(Model = "Linear"),
    broom::tidy(m2, conf.int = TRUE) %>% mutate(Model = "Quadratic"),
    broom::tidy(m3, conf.int = TRUE) %>% mutate(Model = "Piecewise_1knot")
  ) %>%
    mutate(
      Path = label,
      X = x,
      Y = y,
      Covariates = ifelse(length(covariates) > 0, paste(covariates, collapse = ", "), "None"),
      N = nrow(d),
      Knot = ifelse(Model == "Piecewise_1knot", knot, NA_real_),
      p_APA = purrr::map_chr(p.value, fmt_p),
      Significance = purrr::map_chr(p.value, sig_flag)
    )
  
  comp_tbl <- tibble(
    Path = label,
    X = x,
    Y = y,
    Comparison = c("Quadratic vs Linear", "Piecewise vs Linear"),
    F_value = c(
      anova(m1, m2)$F[2],
      anova(m1, m3)$F[2]
    ),
    p_value = c(
      anova(m1, m2)$`Pr(>F)`[2],
      anova(m1, m3)$`Pr(>F)`[2]
    )
  ) %>%
    mutate(
      p_APA = purrr::map_chr(p_value, fmt_p),
      Significance = purrr::map_chr(p_value, sig_flag)
    )
  
  x_seq <- seq(min(d$x_raw), max(d$x_raw), length.out = 300)
  
  pred_grid <- tibble(
    x_raw = x_seq,
    x_sq = x_seq^2,
    x_post = pmax(0, x_seq - knot)
  )
  
  if(length(covariates) > 0){
    for(covariate in covariates){
      pred_grid[[covariate]] <- mean(d[[covariate]], na.rm = TRUE)
    }
  }
  
  pred_tbl <- bind_rows(
    pred_grid %>% mutate(Predicted = predict(m1, newdata = .), Model = "Linear"),
    pred_grid %>% mutate(Predicted = predict(m2, newdata = .), Model = "Quadratic"),
    pred_grid %>% mutate(Predicted = predict(m3, newdata = .), Model = "Piecewise_1knot")
  ) %>%
    mutate(Path = label, X = x, Y = y)
  
  list(
    fit = fit_tbl,
    coef = coef_tbl,
    comp = comp_tbl,
    pred = pred_tbl,
    data = d,
    knot = knot
  )
}

# ------------------------------------------------------------
# Functional-form tests
# ------------------------------------------------------------

res_rifl_rja <- fit_linear_quad_piece(
  df_parent_med, "RIFL_Z", "RJA_Z",
  knot = median(df_parent_med$RIFL_Z, na.rm = TRUE),
  label = "RIFL -> RJA"
)

res_rja_task <- fit_linear_quad_piece(
  df_parent_med, "RJA_Z", "Task_Z",
  knot = median(df_parent_med$RJA_Z, na.rm = TRUE),
  label = "RJA -> Task"
)

parent_shape_fit <- bind_rows(res_rifl_rja$fit, res_rja_task$fit)
parent_shape_coef <- bind_rows(res_rifl_rja$coef, res_rja_task$coef)
parent_shape_comp <- bind_rows(res_rifl_rja$comp, res_rja_task$comp)

write_csv(round_df(parent_shape_fit, 3),
          file.path(reg_dir, "03_ParentLed_FunctionalForm_ModelFit.csv"))

write_csv(round_df(parent_shape_coef, 3),
          file.path(reg_dir, "04_ParentLed_FunctionalForm_Coefficients.csv"))

write_csv(round_df(parent_shape_comp, 3),
          file.path(reg_dir, "05_ParentLed_FunctionalForm_ModelComparisons.csv"))

plot_functional_form <- function(raw_data, pred_data, xvar, yvar, title, xlab, ylab, outfile){
  p <- ggplot(raw_data, aes(x = .data[[xvar]], y = .data[[yvar]])) +
    geom_point(alpha = .50, size = 2.3, colour = "grey35") +
    geom_line(
      data = pred_data,
      aes(x = x_raw, y = Predicted, color = Model),
      linewidth = 1.2
    ) +
    theme_classic(base_size = 14) +
    labs(title = title, x = xlab, y = ylab, color = "Model")
  
  ggsave(file.path(reg_dir, outfile), p, width = 7, height = 5, dpi = 320, bg = "white")
  p
}

p_parent_rifl_rja <- plot_functional_form(
  df_parent_med, res_rifl_rja$pred,
  "RIFL_Z", "RJA_Z",
  "Parent-led path: RIFL -> RJA",
  "RIFL (z)", "RJA (z)",
  "06_FunctionalForm_RIFL_to_RJA.png"
)

p_parent_rja_task <- plot_functional_form(
  df_parent_med, res_rja_task$pred,
  "RJA_Z", "Task_Z",
  "Parent-led path: RJA -> Task",
  "RJA (z)", "Task performance (z)",
  "07_FunctionalForm_RJA_to_Task.png"
)

# ------------------------------------------------------------
# APA one-row summaries
# ------------------------------------------------------------

parent_reg_summary <- parent_reg_coef %>%
  filter(term != "(Intercept)") %>%
  transmute(
    Pathway = Model,
    N,
    b = estimate,
    SE = std.error,
    t = statistic,
    p = p.value,
    CI_low = conf.low,
    CI_high = conf.high,
    p_APA,
    Significance
  )

write_csv(round_df(parent_reg_summary, 3),
          file.path(reg_dir, "08_ParentLed_APA_RegressionSummary.csv"))

parent_shape_summary <- parent_shape_fit %>%
  group_by(Path) %>%
  arrange(AIC, .by_group = TRUE) %>%
  slice(1) %>%
  ungroup() %>%
  transmute(
    Path,
    Best_Model_by_AIC = Model,
    N,
    R2 = r.squared,
    AIC,
    BIC,
    p_APA
  )

write_csv(round_df(parent_shape_summary, 3),
          file.path(reg_dir, "09_ParentLed_APA_FunctionalFormSummary.csv"))

# ======================================================================================
# SECTION 9 — Full-sample parent-led mediation
# ======================================================================================

cat("\n📌 SECTION 9 — Running full-sample mediation...\n")

med_dir <- file.path(out_dir, "Mediation")
dir.create(med_dir, recursive = TRUE, showWarnings = FALSE)

full_med <- run_parent_mediation(
  data = df_parent_med,
  out_prefix = file.path(med_dir, "01_FullSample_RIFL_RJA_Task_AgeCovariate"),
  nboot = 5000
)

fit_med_full <- full_med$fit
params_full <- full_med$params
full_key_tbl <- full_med$key_tbl

png(
  file.path(med_dir, "02_FullSample_Mediation_PathDiagram.png"),
  width = 1200,
  height = 800,
  res = 150
)

semPlot::semPaths(
  fit_med_full,
  whatLabels = "std",
  style = "ram",
  edge.label.cex = 1.2,
  intercepts = FALSE
)

dev.off()

# ======================================================================================
# SECTION 10 — Bivariate vs age-adjusted controlled RJA -> Task
# ======================================================================================

cat("\n📌 SECTION 10 — Comparing RJA -> Task bivariate vs age-adjusted controlled...\n")

mod_rja_task_biv <- lm(Task_Z ~ RJA_Z, data = df_parent_med)
mod_rja_task_age <- lm(Task_Z ~ RJA_Z + ChildAge_Z, data = df_parent_med)
mod_rja_task_controlled <- lm(Task_Z ~ RJA_Z + RIFL_Z + ChildAge_Z, data = df_parent_med)

rja_compare_tbl <- dplyr::bind_rows(
  broom::tidy(mod_rja_task_biv) %>%
    dplyr::filter(term == "RJA_Z") %>%
    dplyr::transmute(
      Comparison = "RJA_to_Task_bivariate",
      est = estimate,
      se = std.error,
      statistic = statistic,
      pvalue = p.value,
      N = nrow(df_parent_med)
    ),
  broom::tidy(mod_rja_task_age) %>%
    dplyr::filter(term == "RJA_Z") %>%
    dplyr::transmute(
      Comparison = "RJA_to_Task_controlling_age",
      est = estimate,
      se = std.error,
      statistic = statistic,
      pvalue = p.value,
      N = nrow(model.frame(mod_rja_task_age))
    ),
  broom::tidy(mod_rja_task_controlled) %>%
    dplyr::filter(term == "RJA_Z") %>%
    dplyr::transmute(
      Comparison = "RJA_to_Task_controlling_RIFL_and_age",
      est = estimate,
      se = std.error,
      statistic = statistic,
      pvalue = p.value,
      N = nrow(model.frame(mod_rja_task_controlled))
    )
) %>%
  dplyr::mutate(Significance = sapply(pvalue, sig_flag))

readr::write_csv(
  rja_compare_tbl,
  file.path(med_dir, "03_RJA_Task_Bivariate_vs_Controlled.csv")
)

# ======================================================================================
# SECTION 11 — Sliding-window mediation
# ======================================================================================

cat("\n📌 SECTION 11 — Running sliding-window mediation...\n")

window_dir <- file.path(out_dir, "SlidingWindow_width35")
dir.create(window_dir, recursive = TRUE, showWarnings = FALSE)

sw_full <- run_quantile_jn_sliding(
  data = df_parent_med,
  out_dir = window_dir,
  prefix = "Study1_N90_width35_AgeCovariate",
  width_q = 0.35,
  step_q = 0.05,
  min_n_in_win = 22,
  nboot = 2000,
  estimator = "ML",
  boot_ci_type = "perc",
  overlap = TRUE,
  n_bins = 6,
  fit_for_pathdiag = fit_med_full,
  params_full = params_full
)

readr::write_csv(
  sw_full$all,
  file.path(window_dir, "01_All_SlidingWindows_width35.csv")
)

readr::write_csv(
  sw_full$sig,
  file.path(window_dir, "02_Significant_SlidingWindows_width35.csv")
)

# ======================================================================================
# SECTION 12 — Confirmatory mediation: 35th–70th percentile RJA window
# ======================================================================================

cat("\n📌 SECTION 12 — Running confirmatory 35th–70th percentile mediation...\n")

confirm_dir <- file.path(out_dir, "Confirmatory_Mediation_35_70")
dir.create(confirm_dir, recursive = TRUE, showWarnings = FALSE)

mid_probs <- c(0.35, 0.70)

mid_rja_bounds <- stats::quantile(
  df_parent_med$RJA_Z,
  probs = mid_probs,
  na.rm = TRUE
)

mid_rja_lo <- unname(mid_rja_bounds[1])
mid_rja_hi <- unname(mid_rja_bounds[2])

df_parent_mid <- df_parent_med %>%
  dplyr::filter(
    RJA_Z >= mid_rja_lo,
    RJA_Z <= mid_rja_hi
  )

readr::write_csv(
  df_parent_mid,
  file.path(confirm_dir, "01_MidRange35_70_Subsample.csv")
)

midrange_def_tbl <- tibble::tibble(
  WindowLabel = "Sliding-window-derived RJA mediation region",
  Quantile_low = 0.35,
  Quantile_high = 0.70,
  Quantile_center = 0.525,
  Window_width = 0.35,
  Definition = "Empirically derived from the significant N90 sliding-window mediation result",
  RJA_Z_low_bound = mid_rja_lo,
  RJA_Z_high_bound = mid_rja_hi,
  N_subsample = nrow(df_parent_mid)
)

readr::write_csv(
  midrange_def_tbl,
  file.path(confirm_dir, "02_MidRange35_70_Definition.csv")
)

mid_med <- run_parent_mediation(
  data = df_parent_mid,
  out_prefix = file.path(confirm_dir, "03_MidRange35_70_AgeCovariate"),
  nboot = 5000
)

mid_key_tbl <- mid_med$key_tbl

mod_mid_biv <- lm(Task_Z ~ RJA_Z, data = df_parent_mid)
mod_mid_age <- lm(Task_Z ~ RJA_Z + ChildAge_Z, data = df_parent_mid)
mod_mid_ctrl <- lm(Task_Z ~ RJA_Z + RIFL_Z + ChildAge_Z, data = df_parent_mid)

mid_rja_compare_tbl <- dplyr::bind_rows(
  broom::tidy(mod_mid_biv) %>%
    dplyr::filter(term == "RJA_Z") %>%
    dplyr::transmute(
      Comparison = "MidRange35_70_RJA_to_Task_bivariate",
      est = estimate,
      se = std.error,
      statistic = statistic,
      pvalue = p.value,
      N = nrow(df_parent_mid)
    ),
  broom::tidy(mod_mid_age) %>%
    dplyr::filter(term == "RJA_Z") %>%
    dplyr::transmute(
      Comparison = "MidRange35_70_RJA_to_Task_controlling_age",
      est = estimate,
      se = std.error,
      statistic = statistic,
      pvalue = p.value,
      N = nrow(model.frame(mod_mid_age))
    ),
  broom::tidy(mod_mid_ctrl) %>%
    dplyr::filter(term == "RJA_Z") %>%
    dplyr::transmute(
      Comparison = "MidRange35_70_RJA_to_Task_controlling_RIFL_and_age",
      est = estimate,
      se = std.error,
      statistic = statistic,
      pvalue = p.value,
      N = nrow(model.frame(mod_mid_ctrl))
    )
) %>%
  dplyr::mutate(Significance = sapply(pvalue, sig_flag))

readr::write_csv(
  mid_rja_compare_tbl,
  file.path(confirm_dir, "04_MidRange35_70_RJA_Task_Bivariate_vs_Controlled.csv")
)

p_mid_a <- make_scatter_lm(
  df_parent_mid,
  "RIFL_Z",
  "RJA_Z",
  "RIFL (z)",
  "RJA (z)",
  "Localized Region: RIFL and Child RJA",
  "13_MidRange35_70_RIFL_RJA.png",
  COL_RJA
)

p_mid_b <- make_scatter_lm(
  df_parent_mid,
  "RJA_Z",
  "Task_Z",
  "RJA (z)",
  "Task performance (z)",
  "Localized Region: RJA and Task Performance",
  "14_MidRange35_70_RJA_Task.png",
  COL_TASK
)

ggplot2::ggsave(
  file.path(confirm_dir, "05_MidRange35_70_RIFL_RJA.png"),
  p_mid_a,
  width = 5.5,
  height = 4.5,
  dpi = 320,
  bg = "white"
)

ggplot2::ggsave(
  file.path(confirm_dir, "06_MidRange35_70_RJA_Task.png"),
  p_mid_b,
  width = 5.5,
  height = 4.5,
  dpi = 320,
  bg = "white"
)

# ======================================================================================
# SECTION 13 — APA summary tables/text
# ======================================================================================

cat("\n📌 SECTION 13 — Writing APA summary...\n")

mid_a <- mid_key_tbl %>%
  dplyr::filter(Effect == "A_path_RIFL_to_RJA") %>%
  dplyr::slice(1)

mid_b <- mid_key_tbl %>%
  dplyr::filter(Effect == "B_path_RJA_to_Task_controlled_RIFL_age") %>%
  dplyr::slice(1)

mid_c <- mid_key_tbl %>%
  dplyr::filter(Effect == "Direct_RIFL_to_Task_cprime") %>%
  dplyr::slice(1)

mid_i <- mid_key_tbl %>%
  dplyr::filter(Effect == "Indirect_RIFL_to_RJA_to_Task") %>%
  dplyr::slice(1)

mid_t <- mid_key_tbl %>%
  dplyr::filter(Effect == "Total") %>%
  dplyr::slice(1)

mid_summary_1row <- tibble::tibble(
  Section = "Study 1 Parent-led calibration",
  Subgroup = "RJA_35_70",
  Quantile_low = 0.35,
  Quantile_high = 0.70,
  RJA_Z_low_bound = mid_rja_lo,
  RJA_Z_high_bound = mid_rja_hi,
  N = nrow(df_parent_mid),
  A_path_est = mid_a$est,
  A_path_p = mid_a$pvalue,
  B_path_est = mid_b$est,
  B_path_p = mid_b$pvalue,
  Direct_est = mid_c$est,
  Direct_p = mid_c$pvalue,
  Indirect_est = mid_i$est,
  Indirect_p = mid_i$pvalue,
  Indirect_CI_low = mid_i$ci.lower,
  Indirect_CI_high = mid_i$ci.upper,
  Total_est = mid_t$est,
  Total_p = mid_t$pvalue,
  Indirect_sig = mid_i$ci.lower > 0 | mid_i$ci.upper < 0
)

readr::write_csv(
  mid_summary_1row,
  file.path(confirm_dir, "07_MidRange35_70_Mediation_Summary_1row.csv")
)

r_rifl_rja <- cor_long %>% dplyr::filter(Var1 == "RJA", Var2 == "RIFL") %>% dplyr::slice(1)
r_rja_task <- cor_long %>% dplyr::filter(Var1 == "Task", Var2 == "RJA") %>% dplyr::slice(1)
r_rifl_task <- cor_long %>% dplyr::filter(Var1 == "Task", Var2 == "RIFL") %>% dplyr::slice(1)

apa_text <- tibble::tibble(
  APA_Text = glue::glue(
    "In the Study 1 analytic sample (N = {nrow(df_parent_med)}), caregiving quality was associated with child RJA, r = {sprintf('%.2f', r_rifl_rja$r)}, p = {fmt_p_apa(r_rifl_rja$p)}. Child RJA was associated with task performance, r = {sprintf('%.2f', r_rja_task$r)}, p = {fmt_p_apa(r_rja_task$p)}. Caregiving quality was also associated with task performance, r = {sprintf('%.2f', r_rifl_task$r)}, p = {fmt_p_apa(r_rifl_task$p)}. Age-adjusted sliding-window analyses identified a developmental region spanning the 35th to 70th percentile of the RJA distribution (RJA z = {round(mid_rja_lo, 2)} to {round(mid_rja_hi, 2)}; N = {nrow(df_parent_mid)}). Within this age-adjusted model, caregiving quality positively predicted child RJA, B = {round(mid_a$est, 3)}, SE = {round(mid_a$se, 3)}, {fmt_p(mid_a$pvalue)}, and child RJA positively predicted task performance after controlling for caregiving quality and child age, B = {round(mid_b$est, 3)}, SE = {round(mid_b$se, 3)}, {fmt_p(mid_b$pvalue)}. The age-adjusted indirect effect was ab = {round(mid_i$est, 3)}, 95% CI [{round(mid_i$ci.lower, 3)}, {round(mid_i$ci.upper, 3)}], {fmt_p(mid_i$pvalue)}."
  )
)

readr::write_csv(
  apa_text,
  file.path(out_dir, "APA_Study1_ParentLed_Calibration_Text.csv")
)

# ======================================================================================
# SECTION 14 — DOCX report
# ======================================================================================

cat("\n📌 SECTION 14 — Writing DOCX report...\n")

doc <- officer::read_docx()

    doc <- doc %>%
  officer::body_add_par("Study 1 — Parent-led Developmental Calibration (Age-Covariate Version)", style = "heading 1") %>%
  officer::body_add_par("Participant characteristics", style = "heading 2") %>%
  flextable::body_add_flextable(flextable::flextable(demo_tbl) %>% flextable::autofit()) %>%
  officer::body_add_par("Core variable descriptives", style = "heading 2") %>%
  flextable::body_add_flextable(flextable::flextable(core_desc_tbl) %>% flextable::autofit()) %>%
  officer::body_add_par("Core variable correlations", style = "heading 2") %>%
  flextable::body_add_flextable(flextable::flextable(cor_apa_tbl) %>% flextable::autofit()) %>%
  officer::body_add_par("Core variable distributions", style = "heading 2") %>%
  officer::body_add_img(file.path(desc_dir, "08_Raincloud_CoreVariables_Combined.png"), width = 6.8, height = 3.4) %>%
  officer::body_add_par("Core bivariate associations", style = "heading 2") %>%
  officer::body_add_img(file.path(desc_dir, "12_Scatter_CoreAssociations_Combined.png"), width = 7.2, height = 2.7) %>%
  officer::body_add_par("Full-sample mediation", style = "heading 2") %>%
  flextable::body_add_flextable(flextable::flextable(full_key_tbl) %>% flextable::autofit()) %>%
  officer::body_add_img(file.path(med_dir, "02_FullSample_Mediation_PathDiagram.png"), width = 6.3, height = 4.2) %>%
  officer::body_add_par("Sliding-window localization", style = "heading 2") %>%
  flextable::body_add_flextable(flextable::flextable(sw_full$sig_summary) %>% flextable::autofit()) %>%
  officer::body_add_img(file.path(window_dir, "06_JN_style_sliding_window_indirects.png"), width = 6.5, height = 4) %>%
  officer::body_add_par("Confirmatory mediation in the 35th–70th percentile RJA region", style = "heading 2") %>%
  flextable::body_add_flextable(flextable::flextable(midrange_def_tbl) %>% flextable::autofit()) %>%
  flextable::body_add_flextable(flextable::flextable(mid_key_tbl) %>% flextable::autofit()) %>%
  officer::body_add_par("APA summary", style = "heading 2") %>%
  officer::body_add_par(apa_text$APA_Text, style = "Normal")

print(
  doc,
  target = file.path(out_dir, "Study1_ParentLed_Calibration_Report.docx")
)

# ======================================================================================
# FINAL CONSOLE SUMMARY
# ======================================================================================

cat("\n✅ STUDY 1 PARENT-LED CALIBRATION AGE-COVARIATE SCRIPT COMPLETED.\n")
cat("Main outputs:\n")
cat("  -", file.path(out_dir, "00_Study1_N90_ModelReady.csv"), "\n")
cat("  -", file.path(desc_dir, "01_APA_ParticipantCharacteristics.csv"), "\n")
cat("  -", file.path(desc_dir, "02_APA_CoreVariable_Descriptives.csv"), "\n")
cat("  -", file.path(desc_dir, "04_APA_CoreVariable_CorrelationTable.csv"), "\n")
cat("  -", file.path(desc_dir, "08_Raincloud_CoreVariables_Combined.png"), "\n")
cat("  -", file.path(desc_dir, "12_Scatter_CoreAssociations_Combined.png"), "\n")
cat("  -", file.path(med_dir, "01_FullSample_RIFL_RJA_Task_AgeCovariate_Mediation_KeyResults.csv"), "\n")
cat("  -", file.path(window_dir, "quantile_JN_window_results.csv"), "\n")
cat("  -", file.path(window_dir, "quantile_JN_sig_windows.csv"), "\n")
cat("  -", file.path(confirm_dir, "07_MidRange35_70_Mediation_Summary_1row.csv"), "\n")
cat("  -", file.path(out_dir, "APA_Study1_ParentLed_Calibration_Text.csv"), "\n")
cat("  -", file.path(out_dir, "Study1_ParentLed_Calibration_Report.docx"), "\n") 
