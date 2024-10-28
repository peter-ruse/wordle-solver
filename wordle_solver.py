import random
import time
from collections import Counter
from pathlib import Path
from select import poll

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


class Wordle:
    wordle_url = "https://www.nytimes.com/games/wordle/index.html"
    continue_button_xpath = (
        "//*[local-name()='button' and @class='purr-blocker-card__button']"
    )
    play_button_xpath = "//*[local-name()='button' and @data-testid='Play']"
    close_icon_xpath = "//*[local-name()='svg' and @data-testid='icon-close']"
    keyboard_button_xpath = "//*[local-name()='button' and @data-key='{char}']"
    game_cell_xpath = "//*[@aria-label='Row {attempt}']/div[{pos}]/div"
    letter_count = dict()
    letters_with_known_count = set()
    correct_letter = [None] * 5
    letters_not_here = [set() for _ in range(5)]
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    driver.implicitly_wait(3)
    driver.get(wordle_url)
    attempt = 1
    hints = []
    enter_char = "↵"

    def populate_guess_words(self):
        with open(Path(__file__).parents[0] / "data" / "words.txt", "r") as f:
            self.guess_words = f.read().splitlines()

    def click_play_button(self):
        WebDriverWait(self.driver, 20, poll_frequency=0.1).until(
            EC.element_to_be_clickable((By.XPATH, self.play_button_xpath))
        ).click()

    def click_close_intro_button(self):
        WebDriverWait(self.driver, 20, poll_frequency=0.1).until(
            EC.element_to_be_clickable((By.XPATH, self.close_icon_xpath))
        ).click()

    def start_game(self):
        self.click_play_button()
        self.click_close_intro_button()

    def press_key(self, char: str, pos: int | None = None):
        def click_successful(driver: WebDriver) -> bool:
            WebDriverWait(self.driver, 20, poll_frequency=0.1).until(
                EC.element_to_be_clickable(
                    (By.XPATH, self.keyboard_button_xpath.format(char=char))
                )
            ).click()

            if pos is not None:
                return (
                    WebDriverWait(driver, 20, poll_frequency=0.1)
                    .until(
                        EC.visibility_of_element_located(
                            (
                                By.XPATH,
                                self.game_cell_xpath.format(
                                    attempt=self.attempt, pos=pos
                                ),
                            )
                        )
                    )
                    .text
                    == char.upper()
                )
            else:
                return True

        WebDriverWait(driver=self.driver, timeout=20, poll_frequency=0.1).until(
            click_successful
        )

    def get_hints(self):
        def _get_hints(driver: WebDriver):
            self.hints = [
                driver.find_element(
                    By.XPATH,
                    self.game_cell_xpath.format(attempt=self.attempt, pos=pos),
                ).get_attribute("data-state")
                for pos in range(1, 6)
            ]

        def all_useful_hints(driver) -> bool:
            _get_hints(driver)
            return all(hint in {"correct", "present", "absent"} for hint in self.hints)

        WebDriverWait(driver=self.driver, timeout=20, poll_frequency=0.1).until(
            all_useful_hints
        )

    def make_guess(self):
        guess_words = []
        for guess_word in self.guess_words:
            letter_count = Counter(guess_word)
            condition_1 = all(
                letter_count.get(letter, 0) >= self.letter_count[letter]
                for letter in self.letter_count
            )
            condition_2 = all(
                letter_count.get(letter, 0) == self.letter_count.get(letter, 0)
                for letter in self.letters_with_known_count
            )
            condition_3 = all(
                letter not in letters_not_here
                for letter, letters_not_here in zip(guess_word, self.letters_not_here)
            )
            condition_4 = all(
                letter == correct_letter
                for letter, correct_letter in zip(guess_word, self.correct_letter)
                if correct_letter
            )

            if condition_1 and condition_2 and condition_3 and condition_4:
                guess_words.append(guess_word)

        self.guess_words = guess_words

        guess_word = random.choice(self.guess_words)

        print(
            f"[ATTEMPT {self.attempt}] number of guess words to choose from: "
            f"{len(self.guess_words)}; choosing '{guess_word}'"
        )

        return guess_word

    def enter_guesses(self):
        while self.attempt <= 6:
            guess_word = self.make_guess()

            for pos, letter in enumerate(guess_word, start=1):
                self.press_key(letter, pos)

            self.press_key(self.enter_char)

            self.get_hints()

            all_correct = True
            letter_count = Counter(guess_word)
            for pos, letter, hint in zip(range(5), guess_word, self.hints):
                match hint:
                    case "correct":
                        self.correct_letter[pos] = letter
                    case "present":
                        self.letters_not_here[pos].add(letter)
                        all_correct = False
                    case "absent":
                        letter_count[letter] -= 1
                        self.letters_with_known_count.add(letter)
                        all_correct = False
                    case _:
                        raise ValueError(f"unexpected hint {hint}")

            if all_correct:
                print("guessed the word! exiting game...")
                break

            for letter in letter_count:
                if letter_count[letter] > self.letter_count.get(letter, 0):
                    self.letter_count[letter] = letter_count[letter]

            self.attempt += 1

    def play_game(self):
        self.populate_guess_words()
        self.start_game()
        self.enter_guesses()
        self.driver.close()


if __name__ == "__main__":
    Wordle().play_game()
