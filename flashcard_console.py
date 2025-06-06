import json
import os
import sys
from typing import List, Dict

def load_flashcards(json_path: str) -> List[Dict[str, str]]:
    """
    Reads a JSON file that must contain a top-level "flashcards" list of objects
    { "question": "...", "answer": "..." }.
    """
    if not os.path.exists(json_path):
        print(f"ERROR: Could not find {json_path}", file=sys.stderr)
        sys.exit(1)

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    flashcards = data.get("flashcards")
    if not isinstance(flashcards, list) or not flashcards:
        print("ERROR: JSON must contain a non-empty 'flashcards' list.", file=sys.stderr)
        sys.exit(1)
    return flashcards

def run_console_flashcards(flashcards: List[Dict[str, str]]) -> List[Dict[str, str or int]]:
    """
    Runs a simple console loop over each flashcard, prompting the user to press Enter
    to reveal the answer, then to type a rating (1, 2, or 3). Returns a list of dicts:
      [ {"question": str, "answer": str, "rating": int}, ... ]
    """
    studied_cards: List[Dict[str, str or int]] = []
    total = len(flashcards)

    print("\n=== Flashcard Review ===\n")
    print("Instructions:")
    print("  1) Read the question displayed.")
    print("  2) Press ENTER to reveal the answer.")
    print("  3) After seeing the answer, type a rating (1=Easy, 2=Medium, 3=Hard).")
    print("  4) Press ENTER to move to the next card.\n")

    for idx, card in enumerate(flashcards, start=1):
        question = card["question"]
        answer = card["answer"]

        print(f"Card {idx}/{total}")
        print("-" * 40)
        print("Q:", question)
        input("\nPress ENTER to show the answer…")

        print("\nA:", answer)
        # Loop until we get a valid rating of 1, 2, or 3
        while True:
            rating_str = input("\nRate this card [1=Easy, 2=Medium, 3=Hard]: ").strip()
            if rating_str in ("1", "2", "3"):
                rating = int(rating_str)
                break
            else:
                print("Invalid input. Please type 1, 2, or 3 and press ENTER.")

        studied_cards.append({
            "question": question,
            "answer": answer,
            "rating": rating
        })

        print("\n" + ("=" * 40) + "\n")

    return studied_cards

if __name__ == "__main__":
    # By default, look for calcitriol_flashcards.json in the current folder
    JSON_PATH = "calcitriol_flashcards.json"

    # If user provided a path argument, use that instead
    if len(sys.argv) > 1:
        JSON_PATH = sys.argv[1]

    flashcards = load_flashcards(JSON_PATH)
    results = run_console_flashcards(flashcards)

    # Once finished, print a summary of what you studied and their ratings
    print("\n=== Study Session Complete ===")
    for i, entry in enumerate(results, start=1):
        print(f"{i}. Q: {entry['question']}")
        print(f"   A: {entry['answer']}")
        print(f"   Rating: {entry['rating']}")
        print("-" * 40)

    # You can now hand `results` off to the rest of your program, save to file, etc.
    # For example, to save to JSON:
    # with open("report.json", "w", encoding="utf-8") as out:
    #     json.dump({"cards": results}, out, indent=2, ensure_ascii=False)
