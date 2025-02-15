"""
--------------------------------------------------------------------------
Measurement Error Analysis of Digital Toxicity and SEM with Extended Plots
KODAQS Assignment: Indicators and Metrics of Data Quality
--------------------------------------------------------------------------
Author: Bastián González-Bustamante
Email: b.a.gonzalez.bustamante@fgga.leidenuniv.nl
Website: bgonzalezbustamante.com
Date: 15 February 2025
--------------------------------------------------------------------------
Description:
This script demonstrates a clean coding workflow for:
 1. Loading and cleaning a Twitter/X toxicity dataset from Hugging Face:
    https://huggingface.co/datasets/bgonzalezbustamante/toxicity-protests-ES
 2. Computing inter-coder reliability (Cohen's Kappa) between two human 
    coders (coder_1 and coder_2).
 3. Deriving a 'ground_truth' binary label from agreement between coder_1 
    and coder_2.
 4. Creating two binary toxicity indicators based on a continuous automated 
    measure obtained with Perspective API (distilled BERT model for toxicity):
    - toxicity_60 = 1 if TOXICITY >= 0.6, else 0
    - toxicity_70 = 1 if TOXICITY >= 0.7, else 0
 5. Computing classification metrics (accuracy, precision, recall, F1-score)
    for each thresholded variable (toxicity_60, toxicity_70), and generating
    confusion matrix plots for each measure.
 6. Plotting a boxplot of the distribution of TOXICITY (continuous variable) 
    by ground_truth.
 7. Fitting a Structural Equation Model (SEM) with 'true_toxic' as a latent 
    variable indicated by:
    - coder_1 (binary)
    - coder_2 (binary)
    - toxicity_60 (binary)
    - toxicity_70 (binary)
 8. Saving a Markdown report (measurement_error_KODAQS_Gonzalez-Bustamante.md)
    containing:
    - Inter-coder reliability (Cohen's Kappa)
    - Classification metrics (accuracy, precision, recall, F1-score)
    - Confusion matrices and distribution plots embedded as images
    - SEM factor loadings (rounded to three decimals)
    - Optionally an embedded path diagram (requires Graphviz installed)
    - Some takeaways and limitations
    - Python library version information
--------------------------------------------------------------------------
Usage:
    python measurement_error_KODAQS_Gonzalez-Bustamante.py
--------------------------------------------------------------------------
Python and library versions:
    Python v3.11.5
    pandas v2.2.3
    numpy v2.1.3
    seaborn v0.13.2
    scikit-learn v1.5.2
    semopy v2.3.11
    graphviz v0.20.3
--------------------------------------------------------------------------
"""

##########################################################################
## 1. Import libraries (with versions)
##########################################################################

## General dependencies
import sys
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt

## scikit-learn metrics
from sklearn.metrics import (
    confusion_matrix,
    cohen_kappa_score,
    accuracy_score,
    precision_score,
    recall_score,
    f1_score
)

## semopy for SEM
from semopy import Model, semplot
from graphviz import ExecutableNotFound

## Function for library version in Markdown report
def print_library_versions() -> str:
    """
    Return a markdown-formatted string with Python library versions
    for reproducibility and transparency.
    """
    import sklearn
    import semopy
    import graphviz

    text = (
        f"**Python version**: {sys.version.split(' ')[0]}\n\n"
        f"**pandas version**: {pd.__version__}\n\n"
        f"**numpy version**: {np.__version__}\n\n"
        f"**seaborn version**: {sns.__version__}\n\n"
        f"**scikit-learn version**: {sklearn.__version__}\n\n"
        f"**semopy version**: {semopy.__version__}\n\n"
        f"**graphviz version**: {graphviz.__version__}\n\n"
    )
    return text

##########################################################################
## 2. Data and plotting functions 
##########################################################################

def load_data(filepath: str) -> pd.DataFrame:
    """
    Load a CSV file into a pandas DataFrame.

    Parameters
    ----------
    filepath : str
        URL to the CSV file.

    Returns
    -------
    pd.DataFrame
        The loaded DataFrame.
    """
    df = pd.read_csv(filepath)
    return df


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean the dataset by:
      - Dropping duplicates based on 'id_obs'.
      - Dropping rows missing coder_1, coder_2, or TOXICITY.

    Parameters
    ----------
    df : pd.DataFrame
        Raw dataset.

    Returns
    -------
    pd.DataFrame
        Cleaned dataset.
    """
    df.drop_duplicates(subset="id_obs", inplace=True)
    df.dropna(subset=["coder_1", "coder_2", "TOXICITY"], inplace=True)
    return df


def save_confusion_matrix_plot(
    df: pd.DataFrame,
    predicted_col: str,
    truth_col: str,
    filename: str
) -> None:
    """
    Generate and save a confusion matrix plot as a PNG file.

    Parameters
    ----------
    df : pd.DataFrame
        Data containing binary columns for prediction and ground-truth.
    predicted_col : str
        Column name for the predicted toxicity (0 or 1).
    truth_col : str
        Column name for the ground-truth (0 or 1).
    filename : str
        Output file name to save the plot.

    Returns
    -------
    None
    """
    cm = confusion_matrix(df[truth_col], df[predicted_col])
    plt.figure(figsize=(4.5, 4))
    sns.heatmap(
        cm,
        annot=True,
        fmt="d",
        cmap="Blues",
        xticklabels=["Pred 0", "Pred 1"],
        yticklabels=["True 0", "True 1"]
    )
    plt.title(f"Confusion Matrix: {predicted_col}")
    plt.ylabel("True Label")
    plt.xlabel("Predicted Label")
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()


def save_toxicity_distribution_plot(df: pd.DataFrame, filename: str) -> None:
    """
    Save a boxplot of the distribution of TOXICITY by ground_truth label.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing 'TOXICITY' and 'ground_truth'.
    filename : str
        File name to save the plot.

    Returns
    -------
    None
    """
    plt.figure(figsize=(8, 6))
    sns.boxplot(x="ground_truth", y="TOXICITY", data=df)
    plt.title("Distribution of TOXICITY by Ground-Truth")
    plt.xlabel("Ground Truth (0 = Non-Toxic, 1 = Toxic)")
    plt.ylabel("TOXICITY Perspective API Score")
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()

##########################################################################
## 3. Metrics and labels
##########################################################################

def compute_inter_rater_reliability(df: pd.DataFrame) -> float:
    """
    Compute Cohen's Kappa for coder_1 and coder_2.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain 'coder_1' and 'coder_2' columns.

    Returns
    -------
    float
        Cohen's Kappa score.
    """
    return cohen_kappa_score(df["coder_1"], df["coder_2"])

def derive_ground_truth(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create 'ground_truth' by labeling a tweet toxic if
    coder_1 == 1 OR coder_2 == 1.

    Parameters
    ----------
    df : pd.DataFrame

    Returns
    -------
    pd.DataFrame
        DataFrame with a new 'ground_truth' column (0 or 1).
    """
    df["ground_truth"] = ((df["coder_1"] == 1) | (df["coder_2"] == 1)).astype(int)
    return df

def create_binary_toxicity_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create binary columns for thresholds 0.6 and 0.7 on TOXICITY:
    - toxicity_60 = 1 if TOXICITY >= 0.6, else 0
    - toxicity_70 = 1 if TOXICITY >= 0.7, else 0

    Parameters
    ----------
    df : pd.DataFrame

    Returns
    -------
    pd.DataFrame
        Updated DataFrame with 'toxicity_60' and 'toxicity_70'.
    """
    df["toxicity_60"] = (df["TOXICITY"] >= 0.6).astype(int)
    df["toxicity_70"] = (df["TOXICITY"] >= 0.7).astype(int)
    return df

def compute_classification_metrics(
    df: pd.DataFrame,
    pred_col: str,
    truth_col: str = "ground_truth"
) -> dict:
    """
    Compute classification metrics: accuracy, precision, recall and F1-score.

    Parameters
    ----------
    df : pd.DataFrame
    pred_col : str
        Name of the binary predicted column (0 or 1).
    truth_col : str, optional
        Name of the ground-truth column, by default 'ground_truth'.

    Returns
    -------
    dict
        Dictionary with 'accuracy', 'precision', 'recall', 'f1_score' for the 
        given columns.
    """
    acc = accuracy_score(df[truth_col], df[pred_col])
    prec = precision_score(df[truth_col], df[pred_col], zero_division=0)
    rec = recall_score(df[truth_col], df[pred_col], zero_division=0)
    f1 = f1_score(df[truth_col], df[pred_col], zero_division=0)

    return {
        "accuracy": round(acc, 3),
        "precision": round(prec, 3),
        "recall": round(rec, 3),
        "f1_score": round(f1, 3)
    }

##########################################################################
## 4. SEM
##########################################################################

def fit_sem_model(df: pd.DataFrame) -> Model:
    """
    Fit a Structural Equation Model (SEM) for latent variable 'true_toxic'
    indicated by coder_1, coder_2, toxicity_60 and toxicity_70.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing coder_1, coder_2, toxicity_60, toxicity_70.

    Returns
    -------
    semopy.Model
        Fitted SEM model object.
    """
    model_spec = """
    true_toxic =~ coder_1 + coder_2 + toxicity_60 + toxicity_70
    """
    sem_model = Model(model_spec)
    sem_model.fit(df)
    return sem_model

def format_sem_table(
    df: pd.DataFrame,
    columns_to_format=None,
    decimals: int = 3
) -> pd.DataFrame:
    """
    Convert numeric values in specific columns to a formatted string
    with the given number of decimals, ignoring non-numeric placeholders
    like '-' or empty strings.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame returned by sem_model.inspect(...)
    columns_to_format : list of str, optional
        Column names to format (e.g., ['Est.', 'Std.Err', 'z-value', 'p-value']).
        If None, defaults to these four.
    decimals : int, optional
        Number of decimal places to format, by default 3

    Returns
    -------
    pd.DataFrame
        A copy of df with selected columns formatted as strings where possible.
    """
    import math

    if columns_to_format is None:
        columns_to_format = ["Estimate", "Est. Std", "Std. Err", "z-value", "p-value"]

    ## Work on a copy so we don't overwrite the original DataFrame
    df_formatted = df.copy()

    ## Helper function: attempt float conversion, otherwise return original
    def format_value(x):
        ## If x is null or a dash-like placeholder, return empty
        if pd.isnull(x) or x == '-':
            return ""
        try:
            ## Convert to float and format
            val = float(x)
            return f"{val:.{decimals}f}"
        except (ValueError, TypeError):
            ## If conversion fails, leave as-is
            return str(x)

    for col in columns_to_format:
        if col in df_formatted.columns:
            df_formatted[col] = df_formatted[col].apply(format_value)

    return df_formatted

##########################################################################
## 5. Main execution flow
##########################################################################

def main() -> None:
    """
    Main orchestration function that:
     1. Loads and cleans data.
     2. Computes Cohen's Kappa.
     3. Derives ground_truth variable.
     4. Creates binary toxicity columns (toxicity_60, toxicity_70).
     5. Computes classification metrics for each threshold and saves confusion 
        matrix plots.
     6. Plots distribution of TOXICITY Perspective API score by ground_truth.
     7. Fits an SEM and prints results (rounded to three decimals for all columns).
     8. Saves a final Markdown report including:
        - Cohen's Kappa
        - Classification metrics for toxicity_60 and toxicity_70
        - Confusion matrix plots, distribution plot
        - SEM factor loadings
        - (Optional) embedded path diagram if Graphviz is installed
        - Python library version info
    """
    ## 1. Load and clean
    filepath = "hf://datasets/bgonzalezbustamante/toxicity-protests-ES/goldstd_protests.csv"
    df_raw = load_data(filepath)
    df_clean = clean_data(df_raw)

    ## 2. Inter-rater reliability
    kappa = compute_inter_rater_reliability(df_clean)

    ## 3. Ground truth
    df_clean = derive_ground_truth(df_clean)

    ## 4. Binary indicators for TOXICITY
    df_clean = create_binary_toxicity_columns(df_clean)

    ## 5. Classification metrics and confusion matrices
    metrics_tox_60 = compute_classification_metrics(df_clean, "toxicity_60", "ground_truth")
    metrics_tox_70 = compute_classification_metrics(df_clean, "toxicity_70", "ground_truth")

    ## Save confusion matrix plots
    save_confusion_matrix_plot(df_clean, "toxicity_60", "ground_truth", "cm_tox_60.png")
    save_confusion_matrix_plot(df_clean, "toxicity_70", "ground_truth", "cm_tox_70.png")

    ## 6. Distribution of TOXICITY by ground_truth
    save_toxicity_distribution_plot(df_clean, "toxicity_distribution.png")

    ## 7. Fit SEM
    sem_model = fit_sem_model(df_clean)
    unstd_raw = sem_model.inspect(std_est=False)
    std_raw   = sem_model.inspect(std_est=True)
    
    ## Format specific columns to 3 decimals
    unstd_fmt = format_sem_table(unstd_raw, decimals=3)
    std_fmt   = format_sem_table(std_raw, decimals=3)

    ## Attempt to generate a path diagram
    diagram_generated = False
    try:
        semplot(sem_model, show=False, plot_covs=True, filename="sem_path.png")
        diagram_generated = True
    except ExecutableNotFound:
        pass

    ## 8. Build Markdown report
    report_text = []
    report_text.append("# Measurement Error Analysis of Digital Toxicity and SEM with Extended Plots\n")
    report_text.append("## KODAQS Assignment: Indicators and Metrics of Data Quality\n")
    report_text.append("**Bastián González-Bustamante**\nb.a.gonzalez.bustamante@fgga.leidenuniv.nl\n")

    ## Overview
    report_text.append("## 1. Overview\n")
    report_text.append(
        "In the previous 'Data Quality Pre-Registration', I reviewed the methodological "
        "execution regarding data quality of the paper 'A Gladiatorial Arena: Incivility "
        "in the Canadian House of Commons,' recently published in the *Journal of Politics*. "
        "This paper focused on the prevalence and evolution of uncivil behaviour in the "
        "Canadian House of Commons. Using machine learning techniques, the authors "
        "analysed a dataset of parliamentary interventions.\n"
    )
    report_text.append(
        "This paper relies on Perspective API to measure incivility using emotional "
        "attributes such as identity attack, insult, profanity, threat and toxicity. "
        "Perspective API is a distilled BERT trained by Jigsaw and Google on millions "
        "of comments from Wikipedia, media and information labelled by crowdsource "
        "raters. Some intrinsic data quality problems were detected associated with "
        "Perspective API's limitations because it was trained for online discussions "
        "rather than parliamentary debates. In addition, the work's absence of "
        "ground-truth evaluations or human-in-the-loop annotations also denoted "
        "a problematic lack of external evidence.\n"
    )
    report_text.append(
        "In this script/report, I focused on a dataset developed on my own in the "
        "framework of a project funded by the OpenAI Academic Programme 2024 to "
        "benchmark Large Language Models’ annotation capabilities "
        "(GitHub repository: https://github.com/training-datalab/gold-standard-toxicity). "
        "We labelled a sample of a novel dataset of political interactions on Twitter "
        "(rebranded as X) to generate ground-truth labels with human coders. Our sample "
        "is balanced considering the probability score of Perspective API, which was "
        "applied to the entire dataset and serves as a baseline. The dataset offers "
        "two annotations per observation, therefore, I am able to compare the Perspective "
        "API score with a human gold standard and conduct a measurement error analysis.\n"
    )
    report_text.append(
        "This is relevant because there are a number of concerns about the validity and "
        "reliability of measures such as Perspective API or other BERT and LLMs "
        "classification outputs. For example, Perspective API's score is a probability "
        "score, and the technical documentation of the model suggests carefully "
        "considering a threshold of 0.70 or even higher for the final classification. "
        "Surprisingly, some comparisons with human annotations have suggested that a "
        "lower threshold could be closer to human judgements. In this vein, a measurement "
        "error of these automated indicators is relevant.\n"
    )

    ## Inter-coder reliability
    report_text.append("## 1. Inter-coder reliability\n")
    report_text.append(f"**Cohen's Kappa = {kappa:.3f}** (between coder_1 and coder_2)\n")
    report_text.append(
        "**Main takeaway:** The inter-coder reliability was excellent. The entire "
        "process involved 7.2 hours of annotation and 1.2 hours of revision on the "
        "online platform Labelbox.\n"
    )

    ## Classification metrics
    report_text.append("## 2. Classification metrics\n")
    report_text.append(
        "The performance metrics are: (i) accuracy that reports the proportion of "
        "correct predictions of the particular classifier in comparison with the "
        "human gold standard; (ii) precision that shows the ability of the "
        "classifier to identify positive predicted values to identify false negatives; "
        "(iii) recall or sensitivity that shows the proportion of correct classifications "
        "among true-positive cases; and (iv) F1-score, a combination of precision "
        "and recall.\n"
    )
    
    report_text.append("**Perspective API threshold = 0.6**\n")
    report_text.append(f"- Accuracy: {metrics_tox_60['accuracy']}\n")
    report_text.append(f"- Precision: {metrics_tox_60['precision']}\n")
    report_text.append(f"- Recall: {metrics_tox_60['recall']}\n")
    report_text.append(f"- F1-score: {metrics_tox_60['f1_score']}\n\n")

    report_text.append("**Perspective API threshold = 0.7**\n")
    report_text.append(f"- Accuracy: {metrics_tox_70['accuracy']}\n")
    report_text.append(f"- Precision: {metrics_tox_70['precision']}\n")
    report_text.append(f"- Recall: {metrics_tox_70['recall']}\n")
    report_text.append(f"- F1-score: {metrics_tox_70['f1_score']}\n\n")

    ## Confusion matrix images
    report_text.append("### Confusion Matrices\n")
    report_text.append("![Confusion Matrix (tox_60)](cm_tox_60.png)\n\n")
    report_text.append("![Confusion Matrix (tox_70)](cm_tox_70.png)\n\n")

    ## Distribution plot
    report_text.append("### Distribution of Perspective API Score by Ground-Truth\n")
    report_text.append("![TOXICITY Distribution](toxicity_distribution.png)\n\n")

    ## Interpretation
    report_text.append(
        "**Main takeaway:** Perspective API with a laxer cut-off threshold at 0.60 is closer "
        "to our ground-truth measure elaborated with human coders.\n"
    )
    
    ## SEM Explanation
    report_text.append("## 3. SEM Results\n")
    report_text.append(
        "The Structural Equation Model (SEM) treats 'true_toxic' as a latent factor "
        "indicated by both human-coded labels (coder_1, coder_2) and threshold-based "
        "binary measures (toxicity_60, toxicity_70). This allows me to integrate multiple "
        "sources of measurement, potentially reducing errors associated with any single "
        "indicator.\n"
    )
    report_text.append(
        "By examining factor loadings for each indicator, I can identify which measures "
        "are most strongly associated with the latent toxicity construct. Higher loadings "
        "imply a more reliable indicator. Moreover, the SEM framework accounts for "
        "measurement error explicitly, providing a more robust estimate of true toxicity.\n"
    )

    ## If diagram was generated, embed in Markdown
    if diagram_generated:
        report_text.append("### Path Diagram\n\n")
        report_text.append("![SEM Diagram](sem_path.png)\n\n")

    ## Build the Markdown report
    report_text.append("### SEM Factor Loadings (Unstandardised)\n\n")
    report_text.append(unstd_fmt.to_markdown(index=False))
    report_text.append("\n\n### SEM Factor Loadings (Standardised)\n\n")
    report_text.append(std_fmt.to_markdown(index=False))
    report_text.append("\n")
    report_text.append(
        "**Main takeaways:** The standardised loadings show that coder_1 and coder_2 have strong "
        "relationships with the underlying latent factor (0.969 and 0.972). This indicates that "
        "the human-coded labels provide the clearest signals of 'true toxicity.' The "
        "threshold-based measures (toxicity_60 and toxicity_70) also significantly reflect the "
        "latent construct but with somewhat lower loadings (0.786 and 0.641), suggesting that "
        "while they do capture some aspects of toxicity, they contribute less variance to the "
        "latent factor than human coders, especially Perspective API with a threshold of 0.70, "
        "which aligns with the classification metrics above.\n"
    )
    report_text.append(
        "**Limitations:** Binary indicators were used for both the human-coded variables and the "
        "Perspective API thresholds. Binary indicators may oversimplify the underlying continuum "
        "of toxicity. In addition, classical SEM with maximum-likelihood estimation may not be "
        "strictly optimal for categorical data, sometimes warranting robust estimators or "
        "specialised approaches (e.g., WLSMV or IRT models). Therefore, these factor loadings "
        "are informative but may slightly misrepresent the nuanced gradations of toxicity.\n"
    )

    ## Library Versions
    report_text.append("## 4. Library versions\n\n")
    report_text.append(print_library_versions())

    final_markdown = "\n".join(report_text)

    ## Save the final Markdown to a file
    with open("measurement_error_KODAQS_Gonzalez-Bustamante.md", "w", encoding="utf-8") as f:
        f.write(final_markdown)

    print("Markdown report saved as 'measurement_error_KODAQS_Gonzalez-Bustamante.md'.")
    print("Confusion matrix plots and TOXICITY distribution plot have been saved.")
    if diagram_generated:
        print("SEM diagram saved as 'sem_path.png'.")
    else:
        print("Diagram not generated (Graphviz not installed or not on PATH).")

##########################################################################
## Script entry point
##########################################################################
if __name__ == "__main__":
    main()