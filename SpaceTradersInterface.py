import http.client
import json
import sqlite3
import datetime

DATABASE_NAME = "SpaceTraderDB.db"

class Game:
    def __init__(self,account_token,database_name):
        self._database = Database(database_name)
        self._agents = []
        self._account_token = account_token
        self._contracts = []
        self._ships = []
        self._connection = http.client.HTTPSConnection("api.spacetraders.io")
        self._request_queue = []
        for agent in self._database.get_agents():
            self._agents.append(agent)
        self._current_agent = None
        
        
    def get_agents(self):
        return self._agents
    
    def create_agent(self,symbol=None,faction=None,response=None,):
        if response == None:
            payload_list = ["{"]
            payload_list.append("'symbol': ")
            payload_list.append(f"'{symbol}'")
            payload_list.append(",\n 'faction': ")
            payload_list.append(f"'{faction}'")
            payload_list.append("}")
            payload = "".join(payload_list)
            headers = {"Content-Type": "application/json",
                       "Authorization": f"Bearer {self._account_token}"}
            new_request = Request("POST","/v2/register",payload,headers,self.create_agent)
            self._request_queue.append(new_request)
        else:
            pass # dont need to worry about this until after server reset
    
    def select_agent(self,agent):
        self._current_agent = agent
    
    def get_current_agent(self):
        return self._current_agent
    
    def list_contracts(self,filter_type=None):
        return self._contracts
            
    def request_contracts(self,response=None):
        if self._current_agent == None:
            print("Can't request contracts before selecting an agent")
            return
        if response == None:
            token = self._current_agent.get_token()
            headers = {"Authorization":f"Bearer {token}"}
            new_request = Request("GET","/v2/my/contracts",headers=headers,after=self.request_contracts)
            self._request_queue.append(new_request)
        else:
            data = response["data"]
            self._contracts = []
            for contract_data in data:
                contract_id = contract_data["id"]
                faction = contract_data["factionSymbol"]
                contract_type = contract_data["type"]
                terms = contract_data["terms"]
                deadline = server_to_datetime(terms["deadline"])
                payment = terms["payment"]
                pay_on_accept = payment["onAccepted"]
                pay_on_fulfill = payment["onFulfilled"]
                accepted = contract_data["accepted"]
                fulfilled = contract_data["fulfilled"]
                accept_deadline = contract_data["deadlineToAccept"]
                match contract_type:
                    case "PROCUREMENT":
                        deliveries = terms["deliver"]
                        new_contract = ProcurementContract(contract_id,faction,contract_type,deadline,pay_on_accept,pay_on_fulfill,accepted,fulfilled,accept_deadline,deliveries)
                self._contracts.append(new_contract)
                
    
    def list_ships(self):
        pass
    
    def request_ships(self,response=None):
        if response == None:
            token = self._current_agent.get_token()
            headers = {"Authorization":f"Bearer {token}"}
            new_request = Request("GET","/v2/my/contracts",headers=headers,after=self.request_contracts)
    
    def get_waypoints(self):
        pass
    
    def handle_requests(self):
        current_request = self._request_queue.pop(0)
        if current_request.command == "GET":
            self._connection.request(current_request.command,current_request.link,headers=current_request.headers)
        else:
            self._connection.request(current_request.command,current_request.link,payload=current_request.payload,headers=current_request.headers)
            
        response = self._connection.getresponse()
        response_headers = response.getheaders()
        response_data = response.read()
        
        if response.status != 200:
            print("bad status: ",response.status)
            return
        if current_request.after == None:
            print(response)
        else:
            response_json = json.loads(response_data) 
            current_request.after(response=response_json)
        
    
class Request:
    def __init__(self,command,link,payload=None,headers=None,after=None):
        self.command = command
        self.link = link
        self.payload = payload
        self.headers = headers
        self.after = after

class Agent:
    def __init__(self,token,symbol,headquarters,credit,starting_faction,ship_count):
        self._token = token
    
    def get_token(self):
        return self._token
    
    def get_symbol(self):
        pass
    
    def get_headquarters(self):
        pass
    
    def get_credits(self):
        pass
    
    def get_starting_faction(self):
        pass
    
    def get_ship_count(self):
        pass

class Database:
    def __init__(self,database_name):
        pass
    
    def get_agents(self,agent_id=None):
        return []
    
    def add_agent(self,agent):
        pass
    
    def update_agent(self,agent):
        pass
    
    def get_contracts(self,filter_type):
        pass
    
    def add_contract(contract):
        pass
    
    def update_contract(contract):
        pass
    
class Contract:
    def __init__(self,contract_id,faction,contract_type,deadline,pay_on_accept,pay_on_fulfill,accepted,fulfilled,accept_deadline):
        self._id = contract_id
        self._faction = faction
        self._contract_type = contract_type
        self._deadline = deadline
        self._pay_on_accept = pay_on_accept
        self._pay_on_fulfill = pay_on_fulfill
        self._accepted = accepted
        self._fulfilled = fulfilled
        self._accept_deadline = accept_deadline
        
    def __repr__(self):
        string_list = []
        string_list.append(self._id)
        string_list.append(self._faction)
        string_list.append(self._contract_type)
        string_list.append(str(self._deadline))
        return "Contract object: " + ", ".join(string_list)
        
    def get_id(self):
        return self._id
    
    def get_faction(self):
        return self._faction
    
    def get_type(self):
        return self._type
    
    def get_deadline(self):
        return self._deadline
    
    def get_payment_amounts(self):
        payment = {"on_accept":self._pay_on_accept,
                   "on_fulfill":self._pay_on_fulfill}
        return payment
    
    def get_states(self):
        states = {"accepted":self._accepted,
                  "fulfilled":self._fulfilled}
        return states
    
    def get_accept_deadline(self):
        return self._accept_deadline
    
class ProcurementContract(Contract):
    def __init__(self,contract_id,faction,contract_type,deadline,pay_on_accept,pay_on_fulfill,accepted,fulfilled,accept_deadline,deliveries):
        super().__init__(contract_id,faction,contract_type,deadline,pay_on_accept,pay_on_fulfill,accepted,fulfilled,accept_deadline)
        self._deliveries = []
        for delivery in deliveries:
            new_delivery = Delivery(self,delivery["tradeSymbol"],delivery["destinationSymbol"],delivery["unitsRequired"],delivery["unitsFulfilled"])
            self._deliveries.append(new_delivery)
            
    def get_deliveries(self):
        return self._deliveries
    
class Delivery:
    def __init__(self,parent,good_type,destination,required,fulfilled):
        self._parent_contract = parent
        self._good_type = good_type
        self._destination = destination
        self._required = required
        self._fulfilled = fulfilled
        
    def get_parent(self):
        return self._parent_contract
    
    def get_good_type(self):
        return self._good_type
    
    def get_destination(self):
        return self._destination
    
    def get_progress(self):
        return (self._required,self._fulfilled)
    
def server_to_datetime(server_time):
    normal_time = datetime.datetime.fromisoformat(server_time)
    
    return normal_time
    
    
with open("AccountToken.txt") as account_file:
    account_token = account_file.read().strip()
    
current_game = Game(account_token,DATABASE_NAME)
    

    
    
    
## test centre

with open("AgentToken.txt") as token_file:
    agent_token = token_file.read().strip()
    
my_agent = Agent(agent_token,None,None,None,None,None)
current_game.select_agent(my_agent)
current_game.request_contracts()
current_game.handle_requests()
print(current_game.list_contracts())
    