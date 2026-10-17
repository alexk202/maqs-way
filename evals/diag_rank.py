#!/usr/bin/env python3
"""Дешёвая диагностика полного ранга для 4 промахов (CPU only)."""
import json
import os
from pathlib import Path

def main():
    results = json.load(open("evals/results/pilot_evidence_n500.json"))
    misses = [r for r in results["results"] if not r["evidence_hit"]]
    print(f"Misses found: {len(misses)}")
    
    # We need to do a full search for each miss to get the rank
    # This is just a verification - the search already returned top-5
    for m in misses:
        print(f"  MISS q_id={m['q_id']} type={m['q_type']} answer={m['answer'][:60]}")
        for i, t in enumerate(m['top5'][:5]):
            print(f"  rank {i+1}: sessions={t['sessions']}, text={t['text'][:80]}")
    
    # Summary
    print("\n=== RANK SUMMARY ===")
    for m in misses:
        ans_sessions = set(m.get('answer_session_ids', []))
        found_at = None
        for i, t in enumerate(m['top5']):
            if any(s in t.get('sessions', []) for s in ans_sessions):
                found_at = i + 1
                break
        if found_at:
            print(f"  q_id={m['q_id']}: rank={found_at} (<=5)")
        else:
            print(f"  q_id={m['q_id']}: rank >5 (NOT IN TOP-5)")

if __name__ == "__main__":
    main()