import random


def play_game():
    secret_number = random.randint(1, 100)
    attempts = 7

    print("=== Number Guessing Game ===")
    print("I'm thinking of a number between 1 to 100.")
    print(f"You have {attempts} attempts to guess it.\n")

    for attempt in range(1, attempts + 1):
        while True:
            try:
                guess = int(input(f"Attempt {attempt}/{attempts} - Enter your guess: "))
            except ValueError:
                print("Invalid input. Please enter an integer.")
                continue

            if 1 <= guess <= 100:
                break

            print("Please enter a number between 1 and 100.")

        if guess == secret_number:
            print(f"\nCongratulations! You guessed the number in {attempt} tries.")
            return
        if guess < secret_number:
            print("Too Low!")
        else:
            print("Too High!")

    print(f"\nGame Over! The secret number was {secret_number}.")

if __name__ == "__main__":
    play_game()               