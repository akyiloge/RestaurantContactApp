from restaurant_contact_agent import RestaurantContactAgent
from dotenv import load_dotenv
import os

from tools.restaurant_tools import RestaurantContactTools


def main():
    load_dotenv()

    # Restaurant list
    restaurants = [
        # "Mangia",
        # "Two Hands",
        # "Pies-N-Thighs",
        # "Gees Caribbean Restaurant",
        "sweetgreen"
    ]

    # tools_helper = RestaurantContactTools(restaurants)
    # s = tools_helper.search_and_extract_contacts("Poppy's")
    # print(s)


    agent = RestaurantContactAgent(restaurants)

    print("Starting restaurant contact search...")
    contacts = agent.run_contact_search()

    agent.print_summary()
    # agent.save_results()


if __name__ == "__main__":
    main()