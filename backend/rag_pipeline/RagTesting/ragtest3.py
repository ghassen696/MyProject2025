"""
Generate publication-ready visualizations for RAG evaluation report
Produces LaTeX-compatible figures and tables
"""

import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from matplotlib.patches import Rectangle

# Set publication style
plt.style.use('seaborn-v0_8-paper')
sns.set_palette("husl")
plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['font.size'] = 10
plt.rcParams['font.family'] = 'serif'


def load_results(filepath="rag_evaluation_results.json"):
    """Load evaluation results"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def create_performance_comparison(results):
    """Create inference time comparison chart"""
    df = pd.DataFrame(results)
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    
    # Average inference time by model
    model_times = df.groupby('model')['inference_time'].agg(['mean', 'std']).reset_index()
    model_times = model_times.sort_values('mean')
    
    ax1.barh(model_times['model'], model_times['mean'], xerr=model_times['std'], 
             capsize=5, color=sns.color_palette("rocket", len(model_times)))
    ax1.set_xlabel('Inference Time (seconds)')
    ax1.set_title('Average Inference Time by Model')
    ax1.grid(axis='x', alpha=0.3)
    
    # Time breakdown
    retrieval_mean = df['retrieval_time'].mean()
    
    time_data = []
    for model in df['model'].unique():
        model_df = df[df['model'] == model]
        time_data.append({
            'Model': model,
            'Retrieval': retrieval_mean,
            'Inference': model_df['inference_time'].mean()
        })
    
    time_df = pd.DataFrame(time_data)
    
    x = np.arange(len(time_df))
    width = 0.35
    
    ax2.bar(x, time_df['Retrieval'], width, label='Retrieval', color='#3498db')
    ax2.bar(x, time_df['Inference'], width, bottom=time_df['Retrieval'], 
            label='Inference', color='#e74c3c')
    
    ax2.set_ylabel('Time (seconds)')
    ax2.set_title('Response Time Breakdown')
    ax2.set_xticks(x)
    ax2.set_xticklabels(time_df['Model'], rotation=45, ha='right')
    ax2.legend()
    ax2.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('figure_performance_comparison.pdf', bbox_inches='tight')
    plt.savefig('figure_performance_comparison.png', bbox_inches='tight')
    print("✅ Saved: figure_performance_comparison.pdf/png")
    plt.close()


def create_quality_metrics_radar(manual_scores):
    """Create radar chart for quality dimensions"""
    # Example manual scores (replace with actual data)
    categories = ['Accuracy', 'Completeness', 'Relevance', 'Citation\nQuality', 'Clarity']
    
    # Mock data - replace with actual manual verification results
    models_data = {
        'LLaMA 3.2 (1B)': [3.8, 3.5, 3.9, 3.6, 4.0],
        'LLaMA 3.2 (3B)': [4.2, 4.0, 4.3, 4.1, 4.2],
        'LLaMA 3.2 (8B)': [4.6, 4.5, 4.7, 4.5, 4.6],
        'Gemma 2 (2B)': [4.3, 4.1, 4.4, 4.2, 4.3],
    }
    
    angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
    angles += angles[:1]  # Complete the circle
    
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(projection='polar'))
    
    colors = sns.color_palette("husl", len(models_data))
    
    for (model, scores), color in zip(models_data.items(), colors):
        scores += scores[:1]  # Complete the circle
        ax.plot(angles, scores, 'o-', linewidth=2, label=model, color=color)
        ax.fill(angles, scores, alpha=0.15, color=color)
    
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories)
    ax.set_ylim(0, 5)
    ax.set_yticks([1, 2, 3, 4, 5])
    ax.set_yticklabels(['1', '2', '3', '4', '5'])
    ax.grid(True)
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
    
    plt.title('Quality Metrics Comparison\n(Manual Verification Scores)', 
              size=12, weight='bold', pad=20)
    
    plt.tight_layout()
    plt.savefig('figure_quality_radar.pdf', bbox_inches='tight')
    plt.savefig('figure_quality_radar.png', bbox_inches='tight')
    print("✅ Saved: figure_quality_radar.pdf/png")
    plt.close()


def create_keyword_score_distribution(results):
    """Create keyword score distribution violin plot"""
    df = pd.DataFrame(results)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Violin plot
    sns.violinplot(data=df, x='model', y='keyword_score', ax=ax, palette='muted')
    
    # Add mean markers
    means = df.groupby('model')['keyword_score'].mean()
    positions = range(len(means))
    ax.scatter(positions, means, color='red', s=100, zorder=3, 
               label='Mean', marker='D')
    
    ax.set_xlabel('Model')
    ax.set_ylabel('Keyword Match Score (%)')
    ax.set_title('Keyword Matching Score Distribution by Model')
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    plt.xticks(rotation=45, ha='right')
    
    plt.tight_layout()
    plt.savefig('figure_keyword_distribution.pdf', bbox_inches='tight')
    plt.savefig('figure_keyword_distribution.png', bbox_inches='tight')
    print("✅ Saved: figure_keyword_distribution.pdf/png")
    plt.close()


def create_speed_vs_quality_scatter(results, manual_df):
    """Create speed vs quality trade-off scatter plot"""
    df = pd.DataFrame(results)
    
    # Aggregate by model
    performance = df.groupby('model').agg({
        'inference_time': 'mean',
        'keyword_score': 'mean'
    }).reset_index()
    
    # Add manual scores (mock data - replace with actual)
    manual_overall = {
        'llama3.2:1b': 3.7,
        'llama3.2:3b': 4.1,
        'llama3.2:latest': 4.5,
        'phi3:mini': 3.9,
        'gemma2:2b': 4.2
    }
    
    performance['overall_quality'] = performance['model'].map(manual_overall)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    colors = sns.color_palette("husl", len(performance))
    
    for idx, (_, row) in enumerate(performance.iterrows()):
        ax.scatter(row['inference_time'], row['overall_quality'], 
                  s=300, color=colors[idx], alpha=0.6, edgecolors='black', linewidth=2)
        ax.annotate(row['model'], (row['inference_time'], row['overall_quality']),
                   xytext=(10, 10), textcoords='offset points', fontsize=9,
                   bbox=dict(boxstyle='round,pad=0.3', facecolor=colors[idx], alpha=0.3))
    
    ax.set_xlabel('Average Inference Time (seconds)')
    ax.set_ylabel('Overall Quality Score (1-5)')
    ax.set_title('Speed vs Quality Trade-off')
    ax.grid(True, alpha=0.3)
    
    # Add "ideal zone"
    ideal_rect = Rectangle((0, 4.0), 6, 1, alpha=0.1, color='green', 
                           label='Ideal Zone (Fast + High Quality)')
    ax.add_patch(ideal_rect)
    ax.legend()
    
    plt.tight_layout()
    plt.savefig('figure_speed_quality_tradeoff.pdf', bbox_inches='tight')
    plt.savefig('figure_speed_quality_tradeoff.png', bbox_inches='tight')
    print("✅ Saved: figure_speed_quality_tradeoff.pdf/png")
    plt.close()


def create_category_performance_heatmap(results):
    """Create heatmap of performance by query category"""
    df = pd.DataFrame(results)
    
    # Pivot table: models x categories
    pivot = df.pivot_table(values='keyword_score', 
                          index='model', 
                          columns='category', 
                          aggfunc='mean')
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    sns.heatmap(pivot, annot=True, fmt='.1f', cmap='RdYlGn', 
                vmin=50, vmax=100, ax=ax, cbar_kws={'label': 'Keyword Score (%)'})
    
    ax.set_title('Keyword Matching Performance by Query Category')
    ax.set_xlabel('Query Category')
    ax.set_ylabel('Model')
    
    plt.tight_layout()
    plt.savefig('figure_category_heatmap.pdf', bbox_inches='tight')
    plt.savefig('figure_category_heatmap.png', bbox_inches='tight')
    print("✅ Saved: figure_category_heatmap.pdf/png")
    plt.close()


def create_latex_tables(results, manual_df=None):
    """Generate LaTeX table code"""
    df = pd.DataFrame(results)
    
    # Performance table
    perf_table = df.groupby('model').agg({
        'retrieval_time': ['mean', 'std'],
        'inference_time': ['mean', 'std'],
        'total_time': ['mean', 'std']
    }).round(2)
    
    with open('table_performance.tex', 'w') as f:
        f.write("% Performance Metrics Table\n")
        f.write("\\begin{table}[h]\n")
        f.write("\\centering\n")
        f.write("\\caption{Performance Metrics by Model}\n")
        f.write("\\label{tab:performance_metrics}\n")
        f.write("\\begin{tabular}{@{}lcccc@{}}\n")
        f.write("\\toprule\n")
        f.write("\\textbf{Model} & \\textbf{Retrieval (s)} & \\textbf{Inference (s)} & \\textbf{Total (s)} & \\textbf{Speedup} \\\\\n")
        f.write("\\midrule\n")
        
        baseline = df[df['model'] == 'llama3.2:latest']['inference_time'].mean()
        
        for model in df['model'].unique():
            model_df = df[df['model'] == model]
            ret_mean = model_df['retrieval_time'].mean()
            ret_std = model_df['retrieval_time'].std()
            inf_mean = model_df['inference_time'].mean()
            inf_std = model_df['inference_time'].std()
            tot_mean = model_df['total_time'].mean()
            tot_std = model_df['total_time'].std()
            speedup = baseline / inf_mean
            
            f.write(f"{model} & {ret_mean:.2f} $\\pm$ {ret_std:.2f} & "
                   f"{inf_mean:.2f} $\\pm$ {inf_std:.2f} & "
                   f"{tot_mean:.2f} $\\pm$ {tot_std:.2f} & "
                   f"{speedup:.1f}$\\times$ \\\\\n")
        
        f.write("\\bottomrule\n")
        f.write("\\end{tabular}\n")
        f.write("\\end{table}\n")
    
    print("✅ Saved: table_performance.tex")
    
    # Quality table (with mock manual data)
    with open('table_quality.tex', 'w') as f:
        f.write("% Quality Metrics Table\n")
        f.write("\\begin{table}[h]\n")
        f.write("\\centering\n")
        f.write("\\caption{Quality Metrics by Model}\n")
        f.write("\\label{tab:quality_metrics}\n")
        f.write("\\begin{tabular}{@{}lccccc@{}}\n")
        f.write("\\toprule\n")
        f.write("\\textbf{Model} & \\textbf{Keyword} & \\textbf{Accuracy} & "
               "\\textbf{Complete-} & \\textbf{Overall} & \\textbf{Hallucin-} \\\\\n")
        f.write(" & \\textbf{Score (\\%)} & \\textbf{(1-5)} & "
               "\\textbf{ness (1-5)} & \\textbf{Rating (1-5)} & \\textbf{ations} \\\\\n")
        f.write("\\midrule\n")
        
        # Add rows with actual/mock data
        f.write("\\bottomrule\n")
        f.write("\\end{tabular}\n")
        f.write("\\end{table}\n")
    
    print("✅ Saved: table_quality.tex")


def generate_all_visualizations():
    """Generate all figures and tables"""
    print("\n" + "="*80)
    print("GENERATING VISUALIZATIONS FOR REPORT")
    print("="*80 + "\n")
    
    # Load results
    results = load_results()
    manual_df = None  # Load if available
    
    # Create all visualizations
    create_performance_comparison(results)
    create_quality_metrics_radar(manual_df)
    create_keyword_score_distribution(results)
    create_speed_vs_quality_scatter(results, manual_df)
    create_category_performance_heatmap(results)
    create_latex_tables(results, manual_df)
    
    print("\n" + "="*80)
    print("ALL VISUALIZATIONS GENERATED")
    print("="*80)
    print("\nGenerated files:")
    print("  • figure_performance_comparison.pdf/png")
    print("  • figure_quality_radar.pdf/png")
    print("  • figure_keyword_distribution.pdf/png")
    print("  • figure_speed_quality_tradeoff.pdf/png")
    print("  • figure_category_heatmap.pdf/png")
    print("  • table_performance.tex")
    print("  • table_quality.tex")
    print("\nInclude in LaTeX with:")
    print("  \\input{table_performance.tex}")
    print("  \\begin{figure}[h]")
    print("    \\centering")
    print("    \\includegraphics[width=0.8\\textwidth]{figure_performance_comparison.pdf}")
    print("    \\caption{Performance Comparison}")
    print("  \\end{figure}")


if __name__ == "__main__":
    generate_all_visualizations()