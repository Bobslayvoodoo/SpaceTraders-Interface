from SpaceTradersInterface import *
import tkinter
from tkinter import ttk

DATABASE_NAME = "SpaceTraderDB.db"
update_dict = {}

class AgentSelect:
    def __init__(self,parent,current_game):
        self._main_frame = ttk.Frame(parent)
        for agent in current_game.get_agents():
            current_agent_frame = ttk.Frame(self._main_frame)
            current_agent_frame.grid()
            agent_symbol_label = ttk.Label(current_agent_frame,text=agent.get_symbol())
            agent_symbol_label.grid(column=0,row=0)
            def select_this_agent():
                current_game.select_agent(agent)
                self._main_frame.master.tab(1,state="normal")
                self._main_frame.master.select(1)
            select_agent_button = ttk.Button(current_agent_frame,text="Select",command=select_this_agent)
            select_agent_button.grid(column=1,row=0)
            
    def get_main_frame(self):
        return self._main_frame

class AgentScreen:
    def __init__(self,parent,current_game):
        self._current_game = current_game
        self._main_frame = ttk.Frame(parent)
        self._update_list = []
        
        self._main_frame.columnconfigure(0,weight=1)
        self._main_frame.columnconfigure(1,weight=2)
        self._main_frame.columnconfigure(2,weight=1)
        
        self._main_frame.rowconfigure(0,weight=1)
        self._main_frame.rowconfigure(1,weight=2)
        self._main_frame.rowconfigure(2,weight=1)
        
        
        
        self._ships_list = self.ShipsList(self._main_frame,self._current_game)
        self._update_list.append(self._ships_list)
        self._ships_frame = self._ships_list.get_main_frame()
        self._ships_frame.grid(column=0,row=0,rowspan=2,sticky="nesw")
        self._ships_frame.columnconfigure(0,weight=1)
        self._ships_frame.rowconfigure(9,weight=1)
        
        
        self._contracts_frame = ttk.LabelFrame(self._main_frame,text="Contracts")
        self._contracts_frame.grid(row=2,column=0,sticky="nesw")
        self._contracts_frame.columnconfigure(0,weight=1)
        self._contracts_frame.rowconfigure(0,weight=1)
        
        self._agent_details = self.AgentDetails(self._main_frame)
        self._update_list.append(self._agent_details)
        self._agent_details_frame = self._agent_details.get_main_frame()
        self._agent_details_frame.grid(row=0,column=1,sticky="nesw")
        self._agent_details_frame.columnconfigure(0,weight=1)
        self._agent_details_frame.rowconfigure(9,weight=1)
        
        self._system_frame =ttk.LabelFrame(self._main_frame,text="Current System")
        self._system_frame.grid(row=2,column=1,sticky="nesw")
        self._system_frame.columnconfigure(0,weight=1)
        self._system_frame.rowconfigure(0,weight=1)
        
        self._map_frame = ttk.Frame(self._main_frame)
        self._map_frame.grid(row=1,column=1,sticky="nesw")
        self._map_frame.columnconfigure(0,weight=1)
        self._map_frame.rowconfigure(0,weight=1)
        
        self._current_ship_frame = ttk.LabelFrame(self._main_frame,text="Current Ship")
        self._current_ship_frame.grid(row=0,column=2,rowspan=2,sticky="nesw")
        self._current_ship_frame.columnconfigure(0,weight=1)
        self._current_ship_frame.rowconfigure(0,weight=1)
        
        
    
        
    def get_main_frame(self):
        return self._main_frame
    
    def update(self):
        for group in self._update_list:
            group.update()
        
        
    class AgentDetails():
        def __init__(self,parent):
            self._main_frame = ttk.LabelFrame(parent,text="Agent")
            self._current_game = current_game
            
            self._symbol_label = ttk.Label(self._main_frame,text="Symbol")
            self._symbol_label.grid(column=0,row=0,sticky="new")
            
            self._headquarters_label = ttk.Label(self._main_frame,text="HQ")
            self._headquarters_label.grid(column=0,row=1,sticky="new")
            
            self._credits_label = ttk.Label(self._main_frame,text="££££££££")
            self._credits_label.grid(column=0,row=2,sticky="new")
            
            self._starting_faction_label = ttk.Label(self._main_frame,text="faction")
            self._starting_faction_label.grid(column=0,row=3,sticky="new")
            
            self._ship_count_label = ttk.Label(self._main_frame,text="ship count")
            self._ship_count_label.grid(column=0,row=4,sticky="new")
            
        def get_main_frame(self):
            return self._main_frame
            
        def update(self):
            agent = self._current_game.get_current_agent()
            symbol = agent.get_symbol()
            self._symbol_label.configure(text=symbol)
            
            headquarters = agent.get_headquarters()
            self._headquarters_label.configure(text=headquarters)
            
            credit_count = agent.get_credits()
            self._credits_label.configure(text="£"+str(credit_count))
            
            starting_faction = agent.get_starting_faction()
            self._starting_faction_label.configure(text=starting_faction)
            
            ship_count = agent.get_ship_count()
            self._ship_count_label.configure(text=str(ship_count)+ " Ships")
            
    class ShipsList:
        def __init__(self,parent,game):
            self._main_frame = ttk.LabelFrame(parent,text="Ships")
            self._game = game
            self._ship_frames = {}
            
        class ShipSummary:
            def __init__(self,parent,ship):
                self._main_frame = ttk.Frame(parent,borderwidth=1,relief="groove")
                self._main_frame.bind("<Enter>", func=lambda _:self._main_frame.config(borderwidth=5))
                self._main_frame.bind("<Leave>", func=lambda _:self._main_frame.config(borderwidth=1))
                self._main_frame.columnconfigure(0,weight=1)
                self._ship = ship
                self._symbol_label = ttk.Label(self._main_frame,text="symbol")
                self._symbol_label.grid(column=0,row=0,sticky="nw")
                self._symbol_label.bind("<Enter>", func=lambda _:self._main_frame.config(borderwidth=5))
                self._symbol_label.bind("<Leave>", func=lambda _:self._main_frame.config(borderwidth=1))
                
                self._faction_label = ttk.Label(self._main_frame,text="faction")
                self._faction_label.grid(column=0,row=1,sticky="nw")
                self._faction_label.bind("<Enter>", func=lambda _:self._main_frame.config(borderwidth=5))
                self._faction_label.bind("<Leave>", func=lambda _:self._main_frame.config(borderwidth=1))
                
                self._role_label = ttk.Label(self._main_frame,text="role")
                self._role_label.grid(column=0,row=2,sticky="nw")
                self._role_label.bind("<Enter>", func=lambda _:self._main_frame.config(borderwidth=5))
                self._role_label.bind("<Leave>", func=lambda _:self._main_frame.config(borderwidth=1))
                
                self.update()
            
            def update(self):
                symbol = self._ship.get_symbol()
                self._symbol_label.configure(text=symbol)
                
                faction = self._ship.get_faction()
                self._faction_label.configure(text=faction)
                
                role = self._ship.get_role()
                self._role_label.configure(text=role)
                
            def get_main_frame(self):
                return self._main_frame
            
        def update(self):
            ship_list = self._game.get_current_agent().get_ships()
            for ship in ship_list.values():
                symbol = ship.get_symbol()
                if symbol in self._ship_frames.keys():
                    self._ship_frames[symbol].update()
                else:
                    new_ship_summary = self.ShipSummary(self._main_frame,ship)
                    new_frame = new_ship_summary.get_main_frame()
                    new_frame.grid(column=0,row=len(self._ship_frames),sticky="nwe")
                    self._ship_frames[symbol] = new_ship_summary
                    
                
            
            
        def get_main_frame(self):
            return self._main_frame
            
          
          
def update_call(name):
    #update_dict[name].update()
    update_dict["agent"].update()

with open("AccountToken.txt") as account_file:
    account_token = account_file.read().strip()   
current_game = Game(account_token,DATABASE_NAME)
current_game.add_listener(update_call)

root = tkinter.Tk(baseName="Space Traders GUI")
root.title("Space Traders GUI")
root.geometry("500x500")
root.columnconfigure(0,weight=1)
root.rowconfigure(0,weight=1)

def request_loop():
    current_game.handle_requests()
    root.after(2000,request_loop)

main_tabs = ttk.Notebook(root)
main_tabs.grid(sticky="nesw")

agent_select = AgentSelect(main_tabs,current_game)
main_tabs.add(agent_select.get_main_frame(),text="Agent Select")

agent_screen = AgentScreen(main_tabs,current_game)
main_tabs.add(agent_screen.get_main_frame(),text="Current Agent",state="disabled")

update_dict["agent"] = agent_screen

root.after(2000,request_loop)
root.mainloop()




