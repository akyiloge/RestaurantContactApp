from langchain.agents import create_react_agent, AgentExecutor
from langchain_openai import ChatOpenAI
from langchain import hub
from tools.restaurant_tools import RestaurantContactTools
import json
import time
from typing import List, Dict

from tools.restaurant_tools import RestaurantContactTools

class RestaurantContactAgent:
    def __init__(self, restaurant_list: List[str], gmail_credentials_info: Dict):
    #def __init__(self, restaurant_list: List[str]):
        self.restaurant_list = restaurant_list
        self.contactTool = RestaurantContactTools(gmail_credentials_info)
        #self.contactTool = RestaurantContactTools()
        self.all_contacts = {}

    # def create_tools(self):
    #     return self.tools_helper.create_tools()

    def run_contact_search(self):

        for restaurant in self.restaurant_list:
            # Step 1 - Get email data
            emailData = self.contactTool.search_and_extract_contacts(restaurant)

            output = self.contactTool.analyze_email_blocks_tool(emailData, restaurant)
            r = 2

            # llm = ChatOpenAI(temperature=0, model_name="gpt-4o-mini")
            #
            # tools = self.create_tools()
            # react_prompt = hub.pull("hwchase17/react")
            # agent = create_react_agent(llm=llm, tools=tools, prompt=react_prompt)
            # agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
            #
            # for restaurant in self.restaurant_list:
            #     print(f"\n{'=' * 50}")
            #     print(f"Processing: {restaurant}")
            #     print(f"{'=' * 50}")
            #
            #     task = f"""Find contacts for "{restaurant}" restaurant using these exact steps:
            #
            #     1. Call Search_Restaurant_Emails with input: {restaurant}
            #     2. You will receive email blocks as output (starting with === EMAIL BLOCK)
            #     3. Call Analyze_Email_Blocks with the COMPLETE email blocks output from step 1
            #     4. Return the final JSON result
            #
            #     IMPORTANT: When calling Analyze_Email_Blocks, copy-paste the ENTIRE output from Search_Restaurant_Emails, not a reference to it."""
            #
            #     try:
            #         result = agent_executor.invoke({"input": task})
            #         output = result["output"]
            #

            try:
                if isinstance(output, dict):
                    return output

                cleaned_output = output.strip()

                if "<thinking>" in cleaned_output and "</thinking>" in cleaned_output:
                    end_thinking = cleaned_output.find("</thinking>")
                    cleaned_output = cleaned_output[end_thinking + 11:].strip()

                json_start = cleaned_output.find("[")
                json_end = cleaned_output.rfind("]") + 1

                if json_start >= 0 and json_end > json_start:
                    json_str = cleaned_output[json_start:json_end]
                else:
                    json_start = cleaned_output.find("{")
                    json_end = cleaned_output.rfind("}") + 1
                    if json_start >= 0 and json_end > json_start:
                        json_str = cleaned_output[json_start:json_end]
                    else:
                        # Markdown code blocks
                        if "```json" in cleaned_output:
                            start = cleaned_output.find("```json") + 7
                            end = cleaned_output.rfind("```")
                            if end > start:
                                json_str = cleaned_output[start:end].strip()
                        elif "```" in cleaned_output:
                            start = cleaned_output.find("```") + 3
                            end = cleaned_output.rfind("```")
                            if end > start:
                                json_str = cleaned_output[start:end].strip()
                        else:
                            json_str = cleaned_output

                # Parse
                parsed = json.loads(json_str)
                self.all_contacts[restaurant] = parsed

            except Exception as e:
                self.all_contacts[restaurant] = {
                    "contacts": [],
                    "parse_error": str(e),
                    "raw_output": output[:500]
                }
        #
        #         time.sleep(2)
        #
        #     except Exception as e:
        #         print(f"Error processing {restaurant}: {e}")
        #         self.all_contacts[restaurant] = f"Error: {e}"

        return self.all_contacts

    # def save_results(self, filename: str = "restaurant_contacts.json"):
    #     with open(filename, 'w', encoding='utf-8') as f:
    #         json.dump(self.all_contacts, f, indent=2, ensure_ascii=False)
    #     print(f"Results saved to {filename}")

    def print_summary(self):
        print(f"\n{'=' * 60}")
        print("RESTAURANT CONTACT SEARCH SUMMARY")
        print(f"{'=' * 60}")

        for restaurant, data in self.all_contacts.items():
            print(f"\n{restaurant}:")
            print("-" * len(restaurant))

            if isinstance(data, dict) and "contacts" in data:
                print(f"Found {len(data['contacts'])} contacts")
                for contact in data['contacts']:
                    print(
                        f"  - {contact.get('contact_person', contact.get('name', 'Unknown'))}: {contact.get('email', 'No email')}")
            else:
                print(json.dumps(data, indent=2))