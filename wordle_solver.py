import os
import random
import time
from collections import Counter

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
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

    def populate_guess_words(self):
        with open(f"{os.path.dirname(os.path.abspath(__file__))}/words.txt", "r") as f:
            self.guess_words = f.read().splitlines()

    def click_continue_button(self):
        try:
            self.driver.find_element(By.XPATH, self.continue_button_xpath).click()
        except:
            pass

    def click_play_button(self):
        try:
            self.driver.find_element(By.XPATH, self.play_button_xpath).click()
        except:
            pass

    def click_close_intro_button(self):
        try:
            self.driver.find_element(By.XPATH, self.close_icon_xpath).click()
        except:
            pass

    def start_game(self):
        self.click_continue_button()
        self.click_play_button()
        self.click_close_intro_button()

    def get_data_state(self, pos):
        return self.driver.find_element(
            By.XPATH, self.game_cell_xpath.format(attempt=self.attempt, pos=pos)
        ).get_attribute("data-state")

    def press_key(self, char):
        self.driver.find_element(
            By.XPATH, self.keyboard_button_xpath.format(char=char)
        ).click()

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

        # of course, update the list of guess words to this narrower list...
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

            # so that the word is typed out at a natural pace,
            # put a delay of 0.2 sec between keystrokes...
            for letter in guess_word:
                self.press_key(letter)
                time.sleep(0.2)

            # press the enter button to submit the word...
            self.press_key("↵")

            # sleep 2 seconds while the hints are populated...
            time.sleep(2)

            all_correct = True
            letter_count = Counter(guess_word)
            for pos, letter in enumerate(guess_word):
                data_state = self.get_data_state(pos + 1)
                if data_state == "correct":
                    self.correct_letter[pos] = letter
                elif data_state == "present":
                    self.letters_not_here[pos].add(letter)
                    all_correct = False
                elif data_state == "absent":
                    letter_count[letter] -= 1
                    self.letters_with_known_count.add(letter)
                    all_correct = False

            if all_correct:
                break

            for letter in letter_count:
                if letter_count[letter] > self.letter_count.get(letter, 0):
                    self.letter_count[letter] = letter_count[letter]

            self.attempt += 1

    def play_game(self):
        self.populate_guess_words()
        self.start_game()
        self.enter_guesses()
        time.sleep(3)
        self.driver.close()


if __name__ == "__main__":
    Wordle().play_game()
