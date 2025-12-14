"""
Manual Verification Script
Allows researcher to manually score RAG responses against documentation
"""

import json
import pandas as pd
from typing import List, Dict

# Verification criteria
VERIFICATION_CRITERIA = {
    "accuracy": {
        "description": "Information is factually correct according to documentation",
        "scale": "1-5 (1=Incorrect, 5=Fully Accurate)"
    },
    "completeness": {
        "description": "Response covers all relevant aspects of the question",
        "scale": "1-5 (1=Incomplete, 5=Comprehensive)"
    },
    "relevance": {
        "description": "Response directly addresses the user's query",
        "scale": "1-5 (1=Off-topic, 5=Highly Relevant)"
    },
    "citation_quality": {
        "description": "Proper use of source references [1], [2]",
        "scale": "1-5 (1=No citations, 5=Well-cited)"
    },
    "clarity": {
        "description": "Response is clear and easy to understand",
        "scale": "1-5 (1=Confusing, 5=Very Clear)"
    }
}


def load_evaluation_results(filepath: str = "rag_evaluation_results.json") -> List[Dict]:
    """Load automated evaluation results"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def create_verification_template(results: List[Dict], output_file: str = "manual_verification_template.csv"):
    """Create CSV template for manual verification"""
    
    verification_data = []
    
    for result in results:
        row = {
            "model": result["model"],
            "query": result["query"],
            "category": result["category"],
            "response": result["response"],
            "response_length": result["response_length"],
            "keyword_score": result["keyword_score"],
            "inference_time": result["inference_time"],
            # Manual scoring columns (to be filled)
            "accuracy_score": "",
            "completeness_score": "",
            "relevance_score": "",
            "citation_quality_score": "",
            "clarity_score": "",
            "contains_hallucination": "",  # Yes/No
            "factual_errors": "",  # Description of errors if any
            "overall_rating": "",  # 1-5
            "notes": ""
        }
        verification_data.append(row)
    
    df = pd.DataFrame(verification_data)
    df.to_csv(output_file, index=False)
    print(f"✅ Created manual verification template: {output_file}")
    print(f"📝 Total responses to verify: {len(verification_data)}")
    return df


def analyze_manual_scores(verified_file: str = "manual_verification_completed.csv") -> pd.DataFrame:
    """Analyze completed manual verification scores"""
    
    df = pd.read_csv(verified_file)
    
    # Calculate average scores per model
    score_columns = ["accuracy_score", "completeness_score", "relevance_score", 
                     "citation_quality_score", "clarity_score", "overall_rating"]
    
    for col in score_columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    summary = df.groupby('model')[score_columns].agg(['mean', 'std']).round(2)
    
    # Count hallucinations
    df['contains_hallucination'] = df['contains_hallucination'].str.lower()
    hallucination_counts = df.groupby('model')['contains_hallucination'].apply(
        lambda x: (x == 'yes').sum()
    )
    
    summary['hallucination_count'] = hallucination_counts
    
    print("\n" + "="*80)
    print("MANUAL VERIFICATION SUMMARY")
    print("="*80)
    print(summary)
    
    return summary


def generate_comparison_table(auto_results: str, manual_results: str):
    """Combine automated and manual evaluation results"""
    
    # Load automated results
    auto_df = pd.read_csv(auto_results)
    
    # Load manual results
    manual_df = pd.read_csv(manual_results)
    
    # Merge on model and query
    combined = pd.merge(
        auto_df[['model', 'query', 'inference_time_mean', 'keyword_score_mean']],
        manual_df.groupby('model').agg({
            'accuracy_score': 'mean',
            'completeness_score': 'mean',
            'overall_rating': 'mean',
            'contains_hallucination': lambda x: (x.str.lower() == 'yes').sum()
        }).reset_index(),
        on='model',
        how='left'
    )
    
    combined.columns = ['Model', 'Query', 'Avg Inference Time (s)', 'Keyword Match (%)', 
                        'Accuracy', 'Completeness', 'Overall Rating', 'Hallucinations']
    
    return combined


def print_instructions():
    """Print instructions for manual verification"""
    
    instructions = """
╔════════════════════════════════════════════════════════════════════════════╗
║                    MANUAL VERIFICATION INSTRUCTIONS                        ║
╚════════════════════════════════════════════════════════════════════════════╝

1. SETUP
   - Open the generated CSV file: manual_verification_template.csv
   - Have the Huawei Cloud Stack documentation readily available
   - Set aside 2-3 hours for thorough verification

2. VERIFICATION PROCESS
   For each response, perform these steps:
   
   a) Read the original query
   b) Read the model's response
   c) Cross-reference with the actual documentation
   d) Score each criterion (1-5):
   
      • accuracy_score: Is the information factually correct?
      • completeness_score: Does it answer the full question?
      • relevance_score: Is it directly relevant to the query?
      • citation_quality_score: Are sources properly cited?
      • clarity_score: Is it easy to understand?
   
   e) Mark hallucinations (Yes/No):
      - Does the response contain information NOT in the docs?
      - Does it make up facts, features, or procedures?
   
   f) Note any factual errors in the "factual_errors" column
   
   g) Assign overall_rating (1-5) based on holistic assessment

3. SCORING GUIDELINES
   
   5 = Excellent    - Perfect or near-perfect response
   4 = Good         - Minor issues, generally accurate
   3 = Fair         - Some problems, partially helpful
   2 = Poor         - Major issues, limited usefulness
   1 = Unacceptable - Incorrect, unhelpful, or dangerous

4. COMMON ISSUES TO WATCH FOR
   
   ✗ Hallucinations (making up features)
   ✗ Outdated information
   ✗ Contradictions with documentation
   ✗ Missing critical details
   ✗ Overly generic responses
   ✗ Incorrect procedures

5. AFTER COMPLETION
   - Save as: manual_verification_completed.csv
   - Run: python manual_verification.py --analyze
   - Results will be combined with automated metrics

═══════════════════════════════════════════════════════════════════════════

"""
    print(instructions)


if __name__ == "__main__":
    import sys
    
    print_instructions()
    
    if "--analyze" in sys.argv:
        # Analyze completed verification
        summary = analyze_manual_scores()
        summary.to_csv("manual_verification_summary.csv")
        print("\n✅ Saved analysis to: manual_verification_summary.csv")
    else:
        # Create verification template
        results = load_evaluation_results()
        create_verification_template(results)
        
        print("\n" + "="*80)
        print("NEXT STEPS:")
        print("="*80)
        print("1. Open: manual_verification_template.csv")
        print("2. Verify each response against documentation")
        print("3. Fill in all score columns (1-5 scale)")
        print("4. Save as: manual_verification_completed.csv")
        print("5. Run: python manual_verification.py --analyze")
        print("="*80)