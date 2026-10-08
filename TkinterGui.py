from SpaceTradersInterface import *
import tkinter
from tkinter import ttk

DATABASE_NAME = "SpaceTraderDB.db"

with open("AccountToken.txt") as account_file:
    account_token = account_file.read().strip()   
current_game = Game(account_token,DATABASE_NAME)
with open("AgentToken.txt") as token_file:
    agent_token = token_file.read().strip()
    
my_agent = Agent(agent_token,None,None,None,None,None)
current_game.select_agent(my_agent)

root = tkinter.Tk(baseName="Space Traders GUI")
root.geometry("500x500")


main_tabs = ttk.Notebook(root)
main_tabs.grid()

agent_select_frame = tkinter.Frame(main_tabs)
main_tabs.add(agent_select_frame,text="Agent Select")






