from selenium import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import openai
import time


class Scrapper:
    def __init__(self, device="web"):
        self.opts = FirefoxOptions()
        self.opts.add_argument("--headless")
        self.opts.add_argument("--disable-gpu")
        self.opts.add_argument("--no-sandbox")

        geckodriver_path = "./geckodriver"  # or "/usr/local/bin/geckodriver"
        driver_service = FirefoxService(executable_path=geckodriver_path)
        self.driver = webdriver.Firefox(service=driver_service, options=self.opts)

    def html(self):
        return self.driver.page_source

    def text_and_links(self):
        html = self.driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text(separator=' ', strip=True)
        links = [(a.get_text(strip=True), a['href']) for a in soup.find_all('a', href=True)]
        return text[:4000], links  # trim text to stay within token limits

    def click_link(self, label):
        links = self.driver.find_elements(By.TAG_NAME, "a")
        for link in links:
            if label.lower() in link.text.lower():
                print(f"🖱️ Clicking on: {link.text}")
                link.click()
                return True
        return False

    def close(self):
        self.driver.quit()


def ask_ai(goal, text, links):
    openai.api_key = "your-api-key"  # ⬅️ replace with your key
    prompt = f"""
You are an intelligent web agent. Your current goal is: "{goal}".

Page content:
\"\"\"
{text}
\"\"\"

Here are the available links:
{[label for label, _ in links]}

Which link should be clicked next? Only respond with the link label. If you're done, respond with "DONE".
"""

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a smart web-surfing agent."},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )

    return response.choices[0].message.content.strip()


def run_ai_agent(start_url, goal, max_steps=5):
    bot = Scrapper()
    bot.driver.get(start_url)

    for step in range(max_steps):
        time.sleep(2)  # Wait for JS to load
        print(f"\n🔄 Step {step + 1}")
        text, links = bot.text_and_links()
        decision = ask_ai(goal, text, links)
        print(f"🤖 AI suggests: {decision}")

        if decision.upper() == "DONE":
            break

        if not bot.click_link(decision):
            print("⚠️ Link not found or clickable. Stopping.")
            break

    final_text, _ = bot.text_and_links()
    bot.close()
    return final_text


# Example usage:
if __name__ == "__main__":
    result = run_ai_agent("https://crypto.news/", goal="Find the latest Bitcoin news")
    print("\n📄 Final result:\n", result[:1000])  # print first 1000 chars
