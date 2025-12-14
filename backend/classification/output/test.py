import json
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (
    confusion_matrix, 
    classification_report, 
    accuracy_score,
    precision_recall_fscore_support,
    cohen_kappa_score
)
from collections import defaultdict
import os

# Set style for better-looking plots
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 10

class ClassificationEvaluator:
    def __init__(self, ground_truth_path, predictions_path):
        """Initialize with paths to ground truth and predictions JSON files."""
        self.ground_truth_path = ground_truth_path
        self.predictions_path = predictions_path
        self.results = {}
        
    def load_data(self):
        """Load and align ground truth and predictions."""
        print("Loading data...")
        
        with open(self.ground_truth_path, 'r') as f:
            ground_truth_data = json.load(f)
        
        with open(self.predictions_path, 'r') as f:
            predictions_data = json.load(f)
        
        # Create dictionaries keyed by chunk_id for easy lookup
        gt_dict = {item['chunk_id']: item for item in ground_truth_data}
        pred_dict = {item['chunk_id']: item for item in predictions_data}
        
        # Find common chunk_ids
        common_ids = set(gt_dict.keys()) & set(pred_dict.keys())
        
        print(f"Ground truth samples: {len(gt_dict)}")
        print(f"Prediction samples: {len(pred_dict)}")
        print(f"Common samples: {len(common_ids)}")
        
        # Align data
        self.y_true = []
        self.y_pred = []
        self.confidences = []
        self.chunk_ids = []
        
        for chunk_id in common_ids:
            self.y_true.append(gt_dict[chunk_id]['category'])
            self.y_pred.append(pred_dict[chunk_id]['category'])
            self.confidences.append(pred_dict[chunk_id].get('confidence', 1.0))
            self.chunk_ids.append(chunk_id)
        
        # Get unique categories
        self.categories = sorted(list(set(self.y_true + self.y_pred)))
        
        print(f"\nCategories found: {len(self.categories)}")
        for cat in self.categories:
            print(f"  - {cat}")
        
    def calculate_metrics(self):
        """Calculate all classification metrics."""
        print("\nCalculating metrics...")
        
        # Basic metrics
        self.results['accuracy'] = accuracy_score(self.y_true, self.y_pred)
        self.results['n_samples'] = len(self.y_true)
        self.results['n_categories'] = len(self.categories)
        
        # Per-class metrics
        precision, recall, f1, support = precision_recall_fscore_support(
            self.y_true, self.y_pred, average=None, labels=self.categories, zero_division=0
        )
        
        # Macro and weighted averages
        p_macro, r_macro, f1_macro, _ = precision_recall_fscore_support(
            self.y_true, self.y_pred, average='macro', zero_division=0
        )
        p_weighted, r_weighted, f1_weighted, _ = precision_recall_fscore_support(
            self.y_true, self.y_pred, average='weighted', zero_division=0
        )
        
        self.results['precision_per_class'] = dict(zip(self.categories, precision))
        self.results['recall_per_class'] = dict(zip(self.categories, recall))
        self.results['f1_per_class'] = dict(zip(self.categories, f1))
        self.results['support_per_class'] = dict(zip(self.categories, support))
        
        self.results['precision_macro'] = p_macro
        self.results['recall_macro'] = r_macro
        self.results['f1_macro'] = f1_macro
        
        self.results['precision_weighted'] = p_weighted
        self.results['recall_weighted'] = r_weighted
        self.results['f1_weighted'] = f1_weighted
        
        # Cohen's Kappa
        self.results['cohen_kappa'] = cohen_kappa_score(self.y_true, self.y_pred)
        
        # Confidence statistics
        self.results['mean_confidence'] = np.mean(self.confidences)
        self.results['std_confidence'] = np.std(self.confidences)
        self.results['min_confidence'] = np.min(self.confidences)
        self.results['max_confidence'] = np.max(self.confidences)
        
        # Confusion matrix
        self.cm = confusion_matrix(self.y_true, self.y_pred, labels=self.categories)
        
        print(f"Accuracy: {self.results['accuracy']:.4f}")
        print(f"F1 Score (Macro): {self.results['f1_macro']:.4f}")
        print(f"Cohen's Kappa: {self.results['cohen_kappa']:.4f}")
        
    def plot_confusion_matrix(self, output_path='confusion_matrix.png'):
        """Generate and save confusion matrix heatmap."""
        plt.figure(figsize=(12, 10))
        
        # Normalize confusion matrix by row (true labels)
        cm_normalized = self.cm.astype('float') / self.cm.sum(axis=1)[:, np.newaxis]
        
        # Create heatmap
        sns.heatmap(cm_normalized, annot=True, fmt='.2f', cmap='Blues',
                    xticklabels=self.categories, yticklabels=self.categories,
                    cbar_kws={'label': 'Proportion'})
        
        plt.title('Normalized Confusion Matrix', fontsize=14, fontweight='bold')
        plt.ylabel('True Category', fontsize=12)
        plt.xlabel('Predicted Category', fontsize=12)
        plt.xticks(rotation=45, ha='right')
        plt.yticks(rotation=0)
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"Confusion matrix saved to: {output_path}")
        
    def plot_per_class_metrics(self, output_path='per_class_metrics.png'):
        """Generate bar plot of per-class precision, recall, and F1."""
        fig, ax = plt.subplots(figsize=(14, 8))
        
        x = np.arange(len(self.categories))
        width = 0.25
        
        precision_vals = [self.results['precision_per_class'][cat] for cat in self.categories]
        recall_vals = [self.results['recall_per_class'][cat] for cat in self.categories]
        f1_vals = [self.results['f1_per_class'][cat] for cat in self.categories]
        
        ax.bar(x - width, precision_vals, width, label='Precision', color='#2E86AB')
        ax.bar(x, recall_vals, width, label='Recall', color='#A23B72')
        ax.bar(x + width, f1_vals, width, label='F1-Score', color='#F18F01')
        
        ax.set_xlabel('Category', fontsize=12)
        ax.set_ylabel('Score', fontsize=12)
        ax.set_title('Per-Class Performance Metrics', fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(self.categories, rotation=45, ha='right')
        ax.legend()
        ax.set_ylim([0, 1.0])
        ax.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"Per-class metrics plot saved to: {output_path}")
        
    def plot_confidence_distribution(self, output_path='confidence_distribution.png'):
        """Generate confidence score distribution plot."""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
        
        # Histogram
        ax1.hist(self.confidences, bins=20, color='#06A77D', alpha=0.7, edgecolor='black')
        ax1.axvline(self.results['mean_confidence'], color='red', linestyle='--', 
                   linewidth=2, label=f"Mean: {self.results['mean_confidence']:.3f}")
        ax1.set_xlabel('Confidence Score', fontsize=12)
        ax1.set_ylabel('Frequency', fontsize=12)
        ax1.set_title('Confidence Score Distribution', fontsize=14, fontweight='bold')
        ax1.legend()
        ax1.grid(axis='y', alpha=0.3)
        
        # Box plot by correctness
        correct = [self.confidences[i] for i in range(len(self.y_true)) 
                   if self.y_true[i] == self.y_pred[i]]
        incorrect = [self.confidences[i] for i in range(len(self.y_true)) 
                     if self.y_true[i] != self.y_pred[i]]
        
        ax2.boxplot([correct, incorrect], labels=['Correct', 'Incorrect'])
        ax2.set_ylabel('Confidence Score', fontsize=12)
        ax2.set_title('Confidence by Prediction Correctness', fontsize=14, fontweight='bold')
        ax2.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"Confidence distribution plot saved to: {output_path}")
        
    def plot_category_distribution(self, output_path='category_distribution.png'):
        """Generate category distribution comparison."""
        from collections import Counter
        
        true_counts = Counter(self.y_true)
        pred_counts = Counter(self.y_pred)
        
        fig, ax = plt.subplots(figsize=(14, 8))
        
        x = np.arange(len(self.categories))
        width = 0.35
        
        true_vals = [true_counts.get(cat, 0) for cat in self.categories]
        pred_vals = [pred_counts.get(cat, 0) for cat in self.categories]
        
        ax.bar(x - width/2, true_vals, width, label='Ground Truth', color='#4A5899')
        ax.bar(x + width/2, pred_vals, width, label='Predictions', color='#F26419')
        
        ax.set_xlabel('Category', fontsize=12)
        ax.set_ylabel('Count', fontsize=12)
        ax.set_title('Category Distribution: Ground Truth vs Predictions', 
                     fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(self.categories, rotation=45, ha='right')
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"Category distribution plot saved to: {output_path}")
        
    def generate_latex_report(self, output_path='classification_results.tex'):
        """Generate LaTeX code for the report."""
        latex_content = r"""\subsection{Classification Performance Evaluation}

This section presents the evaluation of the automated activity classification system against manually labeled ground truth data.

\subsubsection{Dataset Overview}

The evaluation dataset consists of \textbf{%%N_SAMPLES%%} employee activity chunks spanning \textbf{%%N_CATEGORIES%%} distinct categories. The classification system achieved an overall accuracy of \textbf{%%ACCURACY%%\%}.

\subsubsection{Performance Metrics}

Table~\ref{tab:classification_metrics} summarizes the overall performance metrics of the classification system.

\begin{table}[h]
\centering
\caption{Overall Classification Performance Metrics}
\label{tab:classification_metrics}
\begin{tabular}{lc}
\hline
\textbf{Metric} & \textbf{Score} \\
\hline
Accuracy & %%ACCURACY%%\% \\
Precision (Macro) & %%PRECISION_MACRO%% \\
Recall (Macro) & %%RECALL_MACRO%% \\
F1-Score (Macro) & %%F1_MACRO%% \\
Precision (Weighted) & %%PRECISION_WEIGHTED%% \\
Recall (Weighted) & %%RECALL_WEIGHTED%% \\
F1-Score (Weighted) & %%F1_WEIGHTED%% \\
Cohen's Kappa & %%COHEN_KAPPA%% \\
\hline
\end{tabular}
\end{table}

The Cohen's Kappa score of \textbf{%%COHEN_KAPPA%%} indicates %%KAPPA_INTERPRETATION%% agreement between the automated classification and ground truth labels.

\subsubsection{Per-Category Performance}

Table~\ref{tab:per_category_metrics} presents the detailed performance metrics for each activity category.

\begin{table}[h]
\centering
\caption{Per-Category Classification Metrics}
\label{tab:per_category_metrics}
\small
\begin{tabular}{lcccr}
\hline
\textbf{Category} & \textbf{Precision} & \textbf{Recall} & \textbf{F1-Score} & \textbf{Support} \\
\hline
%%PER_CLASS_ROWS%%
\hline
\end{tabular}
\end{table}

Figure~\ref{fig:per_class_metrics} visualizes the precision, recall, and F1-score for each category, providing insight into which categories are classified most reliably.

\begin{figure}[h]
\centering
\includegraphics[width=0.9\textwidth]{per_class_metrics.png}
\caption{Per-Category Performance Metrics}
\label{fig:per_class_metrics}
\end{figure}

\subsubsection{Confusion Matrix Analysis}

The confusion matrix in Figure~\ref{fig:confusion_matrix} shows the distribution of predictions across categories. Darker cells along the diagonal indicate correct classifications, while off-diagonal cells represent misclassifications.

\begin{figure}[h]
\centering
\includegraphics[width=0.9\textwidth]{confusion_matrix.png}
\caption{Normalized Confusion Matrix}
\label{fig:confusion_matrix}
\end{figure}

%%CONFUSION_ANALYSIS%%

\subsubsection{Confidence Score Analysis}

The classification system assigns a confidence score to each prediction, representing the certainty of the classification. Figure~\ref{fig:confidence_dist} shows the distribution of confidence scores.

\begin{figure}[h]
\centering
\includegraphics[width=0.9\textwidth]{confidence_distribution.png}
\caption{Confidence Score Distribution and Analysis}
\label{fig:confidence_dist}
\end{figure}

The mean confidence score is \textbf{%%MEAN_CONFIDENCE%%} with a standard deviation of \textbf{%%STD_CONFIDENCE%%}. Confidence scores range from %%MIN_CONFIDENCE%% to %%MAX_CONFIDENCE%%.

\subsubsection{Category Distribution}

Figure~\ref{fig:category_dist} compares the distribution of categories in the ground truth data versus the predictions, highlighting any systematic biases in the classification system.

\begin{figure}[h]
\centering
\includegraphics[width=0.9\textwidth]{category_distribution.png}
\caption{Category Distribution: Ground Truth vs Predictions}
\label{fig:category_dist}
\end{figure}

\subsubsection{Discussion}

%%DISCUSSION_PLACEHOLDER%%
"""
        
        # Generate per-class rows for LaTeX table
        per_class_rows = []
        for cat in self.categories:
            cat_escaped = cat.replace('_', r'\_').replace('&', r'\&')
            precision = self.results['precision_per_class'][cat]
            recall = self.results['recall_per_class'][cat]
            f1 = self.results['f1_per_class'][cat]
            support = int(self.results['support_per_class'][cat])
            
            row = f"{cat_escaped} & {precision:.3f} & {recall:.3f} & {f1:.3f} & {support} \\\\"
            per_class_rows.append(row)
        
        # Interpret Cohen's Kappa
        kappa = self.results['cohen_kappa']
        if kappa < 0:
            kappa_interp = "poor"
        elif kappa < 0.20:
            kappa_interp = "slight"
        elif kappa < 0.40:
            kappa_interp = "fair"
        elif kappa < 0.60:
            kappa_interp = "moderate"
        elif kappa < 0.80:
            kappa_interp = "substantial"
        else:
            kappa_interp = "almost perfect"
        
        # Generate confusion analysis
        confusion_analysis = self._analyze_confusion_matrix()
        
        # Replace placeholders
        latex_content = latex_content.replace('%%N_SAMPLES%%', str(self.results['n_samples']))
        latex_content = latex_content.replace('%%N_CATEGORIES%%', str(self.results['n_categories']))
        latex_content = latex_content.replace('%%ACCURACY%%', f"{self.results['accuracy']*100:.2f}")
        latex_content = latex_content.replace('%%PRECISION_MACRO%%', f"{self.results['precision_macro']:.3f}")
        latex_content = latex_content.replace('%%RECALL_MACRO%%', f"{self.results['recall_macro']:.3f}")
        latex_content = latex_content.replace('%%F1_MACRO%%', f"{self.results['f1_macro']:.3f}")
        latex_content = latex_content.replace('%%PRECISION_WEIGHTED%%', f"{self.results['precision_weighted']:.3f}")
        latex_content = latex_content.replace('%%RECALL_WEIGHTED%%', f"{self.results['f1_weighted']:.3f}")
        latex_content = latex_content.replace('%%F1_WEIGHTED%%', f"{self.results['f1_weighted']:.3f}")
        latex_content = latex_content.replace('%%COHEN_KAPPA%%', f"{self.results['cohen_kappa']:.3f}")
        latex_content = latex_content.replace('%%KAPPA_INTERPRETATION%%', kappa_interp)
        latex_content = latex_content.replace('%%PER_CLASS_ROWS%%', '\n'.join(per_class_rows))
        latex_content = latex_content.replace('%%MEAN_CONFIDENCE%%', f"{self.results['mean_confidence']:.3f}")
        latex_content = latex_content.replace('%%STD_CONFIDENCE%%', f"{self.results['std_confidence']:.3f}")
        latex_content = latex_content.replace('%%MIN_CONFIDENCE%%', f"{self.results['min_confidence']:.3f}")
        latex_content = latex_content.replace('%%MAX_CONFIDENCE%%', f"{self.results['max_confidence']:.3f}")
        latex_content = latex_content.replace('%%CONFUSION_ANALYSIS%%', confusion_analysis)
        
        # Save LaTeX file
        with open(output_path, 'w') as f:
            f.write(latex_content)
        
        print(f"\nLaTeX report saved to: {output_path}")
        
    def _analyze_confusion_matrix(self):
        """Generate textual analysis of confusion matrix."""
        # Find most common misclassifications
        misclassifications = []
        for i, true_cat in enumerate(self.categories):
            for j, pred_cat in enumerate(self.categories):
                if i != j and self.cm[i, j] > 0:
                    proportion = self.cm[i, j] / self.cm[i, :].sum()
                    misclassifications.append((true_cat, pred_cat, self.cm[i, j], proportion))
        
        # Sort by count
        misclassifications.sort(key=lambda x: x[2], reverse=True)
        
        # Generate analysis text
        if len(misclassifications) == 0:
            return "The classifier achieved perfect classification with no misclassifications."
        
        analysis = "Key observations from the confusion matrix:\n\n\\begin{itemize}\n"
        
        # Top 3 misclassifications
        for i, (true_cat, pred_cat, count, prop) in enumerate(misclassifications[:3]):
            true_escaped = true_cat.replace('_', r'\_').replace('&', r'\&')
            pred_escaped = pred_cat.replace('_', r'\_').replace('&', r'\&')
            analysis += f"\\item \\textbf{{{count}}} instances ({prop*100:.1f}\\%) of \\textit{{{true_escaped}}} were misclassified as \\textit{{{pred_escaped}}}\n"
        
        analysis += "\\end{itemize}\n"
        
        return analysis
    
    def save_results_json(self, output_path='classification_results.json'):
        """Save all results to JSON file."""
        # Convert numpy types to Python types for JSON serialization
        results_json = {
            'overall_metrics': {
                'accuracy': float(self.results['accuracy']),
                'precision_macro': float(self.results['precision_macro']),
                'recall_macro': float(self.results['recall_macro']),
                'f1_macro': float(self.results['f1_macro']),
                'precision_weighted': float(self.results['precision_weighted']),
                'recall_weighted': float(self.results['recall_weighted']),
                'f1_weighted': float(self.results['f1_weighted']),
                'cohen_kappa': float(self.results['cohen_kappa']),
                'n_samples': int(self.results['n_samples']),
                'n_categories': int(self.results['n_categories'])
            },
            'confidence_stats': {
                'mean': float(self.results['mean_confidence']),
                'std': float(self.results['std_confidence']),
                'min': float(self.results['min_confidence']),
                'max': float(self.results['max_confidence'])
            },
            'per_category_metrics': {}
        }
        
        for cat in self.categories:
            results_json['per_category_metrics'][cat] = {
                'precision': float(self.results['precision_per_class'][cat]),
                'recall': float(self.results['recall_per_class'][cat]),
                'f1': float(self.results['f1_per_class'][cat]),
                'support': int(self.results['support_per_class'][cat])
            }
        
        with open(output_path, 'w') as f:
            json.dump(results_json, f, indent=2)
        
        print(f"Results JSON saved to: {output_path}")
    
    def run_full_evaluation(self, output_dir='results'):
        """Run complete evaluation pipeline."""
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        print("="*60)
        print("CLASSIFICATION EVALUATION PIPELINE")
        print("="*60)
        
        # Load data
        self.load_data()
        
        # Calculate metrics
        self.calculate_metrics()
        
        # Generate plots
        print("\nGenerating visualizations...")
        self.plot_confusion_matrix(os.path.join(output_dir, 'confusion_matrix.png'))
        self.plot_per_class_metrics(os.path.join(output_dir, 'per_class_metrics.png'))
        self.plot_confidence_distribution(os.path.join(output_dir, 'confidence_distribution.png'))
        self.plot_category_distribution(os.path.join(output_dir, 'category_distribution.png'))
        
        # Generate reports
        print("\nGenerating reports...")
        self.generate_latex_report(os.path.join(output_dir, 'classification_results.tex'))
        self.save_results_json(os.path.join(output_dir, 'classification_results.json'))
        
        print("\n" + "="*60)
        print("EVALUATION COMPLETE!")
        print("="*60)
        print(f"\nAll outputs saved to: {output_dir}/")
        print("\nGenerated files:")
        print("  - confusion_matrix.png")
        print("  - per_class_metrics.png")
        print("  - confidence_distribution.png")
        print("  - category_distribution.png")
        print("  - classification_results.tex")
        print("  - classification_results.json")


def main():
    """Main execution function."""
    # Update these paths to match your files
    ground_truth_path = "ground_truth_classifications.json"
    predictions_path = "employee_classifications_2025-10-28.json"
    
    # Create evaluator
    evaluator = ClassificationEvaluator(ground_truth_path, predictions_path)
    
    # Run full evaluation
    evaluator.run_full_evaluation(output_dir='classification_results')


if __name__ == "__main__":
    main()