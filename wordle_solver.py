import random
from collections import Counter
from pathlib import Path

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
    min_letter_count = dict()
    correct_letter = [None] * 5
    letters_not_here = [set() for _ in range(5)]
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
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

    def enter_guess(self):
        self.guess_word = random.choice(self.guess_words)

        print(
            f"[ATTEMPT {self.attempt}] number of guess words to choose from: "
            f"{len(self.guess_words)}; choosing '{self.guess_word}'"
        )

        for pos, letter in enumerate(self.guess_word, start=1):
            self.press_key(letter, pos)

        self.press_key(self.enter_char)

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

    def use_hints(self):
        letter_count = Counter(self.guess_word)

        for pos, letter, hint in zip(range(5), self.guess_word, self.hints):
            match hint:
                case "correct":
                    self.correct_letter[pos] = letter
                case "present":
                    self.letters_not_here[pos].add(letter)
                case "absent":
                    letter_count[letter] -= 1
                    self.letter_count[letter] = letter_count[letter]
                    self.letters_not_here[pos].add(letter)
                case _:
                    raise ValueError(f"unexpected hint {hint}")

        for letter, count in letter_count.items():
            if count > self.min_letter_count.get(letter, 0):
                self.min_letter_count[letter] = count

    def guessed_word(self):
        return all(letter is not None for letter in self.correct_letter)

    def update_guess_words(self):
        def still_valid(word):
            letter_count = Counter(word)
            return (
                all(
                    letter_count.get(letter, 0) >= min_letter_count
                    for letter, min_letter_count in self.min_letter_count.items()
                )
                and all(
                    letter_count.get(letter, 0) == count
                    for letter, count in self.letter_count.items()
                )
                and all(
                    letter not in letters_not_here
                    for letter, letters_not_here in zip(word, self.letters_not_here)
                )
                and all(
                    letter == correct_letter
                    for letter, correct_letter in zip(word, self.correct_letter)
                    if correct_letter is not None
                )
            )

        self.guess_words = [word for word in self.guess_words if still_valid(word)]

    def enter_guesses(self):
        while self.attempt <= 6 and not self.guessed_word():
            self.enter_guess()
            self.get_hints()
            self.use_hints()
            self.update_guess_words()
            self.attempt += 1

    def play_game(self):
        self.populate_guess_words()
        self.start_game()
        self.enter_guesses()


if __name__ == "__main__":
    Wordle().play_game()
