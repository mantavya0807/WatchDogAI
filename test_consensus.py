"""
Test the consensus-based PII detection system
"""

import sys
sys.path.insert(0, 'src')

from detectors.consensus_detector import ConsensusDetector, visualize_consensus

# Test text with lots of PII
test_text = open('employee_record.txt', 'r', encoding='utf-8').read()

print("="*80)
print("TESTING CONSENSUS-BASED PII DETECTION")
print("="*80)

print("\nTest modes:")
print("1. ANY_TWO: Requires at least 2 detectors to agree (RECOMMENDED)")
print("2. MAJORITY: Requires >50% of detectors to agree")
print("3. UNANIMOUS_STRUCTURED: All detectors for structured data, 2+ for entities")
print("4. STRICT: Requires ALL detectors to agree (most conservative)")

# Test with ANY_TWO mode (recommended)
print("\n" + "="*80)
print("RUNNING CONSENSUS MODE: ANY_TWO (At least 2 detectors must agree)")
print("="*80)

detector = ConsensusDetector(
    consensus_mode='any_two',
    use_parallel=True,
    confidence_threshold=0.5,
    transformer_models=[
        "lakshyakh93/deberta_finetuned_pii",
        # Optionally add a second transformer for stronger consensus
        # "obi/deid_roberta_i2b2"
    ]
)

results = detector.detect(test_text)

# Visualize results
visualize_consensus(test_text, results)

print("\n" + "="*80)
print("CONSENSUS DETECTION COMPLETE")
print("="*80)
print(f"\nTotal high-confidence PII items: {len(results)}")
print("\nBreakdown by type:")

from collections import Counter
type_counts = Counter(r.entity_type for r in results)
for entity_type, count in type_counts.most_common():
    print(f"  {entity_type:15}: {count}")

print("\nVote distribution:")
vote_dist = Counter(r.vote_count for r in results)
for votes, count in sorted(vote_dist.items()):
    print(f"  {votes} votes: {count} items")

print("\n✓ Test complete!")
