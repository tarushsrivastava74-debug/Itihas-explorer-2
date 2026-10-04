import quiz as quiz

TOPIC = "Buddhism & Jainism" 
""  # change this to test different topics

def play():
    path = "round1"
    while True:
        node = quiz.get_quiz_node(TOPIC, path)

        if node is None:
            print(f"\n[ERROR] No node found for path '{path}' — broken 'next' link somewhere.")
            break

        if path.startswith("ending_"):
            print(f"\n=== ENDING: {node['title']} ===")
            print(node["story"])
            break

        print(f"\n{node['question']}\n")
        for key, opt in node["options"].items():
            print(f"  {key}) {opt['text']}")

        choice = input("\nChoose (A/B): ").strip().upper()
        opt = node["options"].get(choice)

        if opt is None:
            print("Invalid choice, try again.")
            continue

        print(f"\n>> {opt['consequence']}")
        path = opt["next"]


if __name__ == "__main__":
    play()
