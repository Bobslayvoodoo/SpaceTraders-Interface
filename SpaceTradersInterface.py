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
            new_agent = Agent(agent_tuple=agent)
            self._agents.append(new_agent)
        self._current_agent = None
        
    def get_agents(self):
        if len(self._agents) == 0:
            agent_list = self._database.get_agents()
            for agent in agent_list:
                print(agent)
        return self._agents
    
    def register_agent(self,symbol=None,faction=None,response=None,):
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
        
    def add_agent(self,agent_token=None,response=None):
        if agent_token:
            headers = {"Authorization":f"Bearer {agent_token}"}
            new_request = Request("GET","/v2/my/agent",headers=headers,after=self.add_agent)
            self._request_queue.append(new_request)
        if response:
            response["data"]["token"] = agent_token
            new_agent = Agent(response["data"])
            command = """
                SELECT * FROM Agents
                WHERE Symbol = ?
                """
            if len(list(self._database.execute(command,new_agent.get_symbol()))) < 1:
                command = """
                    INSERT INTO Agents
                    VALUES (?,?)
                    """
                self._agents.append(new_agent)
                self._database.execute(command,new_agent.get_symbol(),new_agent.get_token())
    
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
        return self._ships
    
    def request_ships(self,response=None):
        if response == None:
            token = self._current_agent.get_token()
            headers = {"Authorization":f"Bearer {token}"}
            new_request = Request("GET","/v2/my/ships",headers=headers,after=self.request_ships)
            self._request_queue.append(new_request)
        else:
            self._ships = []
            ships_list = response["data"]
            for ship_dict in ships_list:
                new_ship = Ship(ship_dict)
                self._ships.append(new_ship)
    
    def get_waypoints(self):
        pass
    
    def handle_requests(self):
        if len(self._request_queue) < 1:
            return
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
            print(response_data)
            return
        if current_request.after == None:
            print(response_data)
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
    def __init__(self,agent_dict=None,agent_tuple=None):
        if agent_dict:
            self._token = agent_dict["token"]
            self._symbol = agent_dict["symbol"]
            self._headquarters = agent_dict["headquarters"]
            self._credits = agent_dict["credits"]
            self._starting_faction = agent_dict["startingFaction"]
            self._ship_count = agent_dict["shipCount"]
        else:
            self._token = agent_tuple[1]
            self._symbol = agent_tuple[0]
            self._headquarters = None
            self._credits = None
            self._starting_faction = None
            self._ship_count = None
        
    def __repr__(self):
        return f"Agent-{self._symbol}"
    
    def get_token(self):
        return self._token
    
    def get_symbol(self):
        return self._symbol
    
    def get_headquarters(self):
        return self._headquarters
    
    def get_credits(self):
        return self._credits
    
    def set_credits(self,new_credits):
        self._credits = new_credits
    
    def get_starting_faction(self):
        return self._starting_faction
    
    def get_ship_count(self):
        return self._ship_count
    
    def set_ship_count(self,new_ship_count):
        self._ship_count = new_ship_count

class Database:
    def __init__(self,database_name):
        self._database_name = database_name
        command = """
            CREATE TABLE IF NOT EXISTS Agents (
               Symbol TEXT,
               Token TEXT
               )
            """
        self.execute(command)
        
    def execute(self,command,*args):
        with sqlite3.connect(self._database_name) as connection:
            cursor = connection.cursor()
            result = cursor.execute(command,args)
        return result
    
    def get_agents(self,agent_symbol=None):
        if agent_symbol == None:
            command = """
                SELECT * FROM Agents
                    """
            return self.execute(command)
            
        command = """
            SELECT * FROM Agents
            WHERE Symbol = ?
                """
        return self.execute(command,agent_symbol)
    
    
    def add_agent(self,agent):
        agent_token = agent.get_token()
        agent_symbol = agent.get_symbol()
        command = """
            INSERT INTO Agents
            VALUES (?, ?)
                """
        self.execute(command,agent_token,agent_symbol)
    
#     def update_agent(self,agent):
#         pass
#     
#     def get_contracts(self,filter_type):
#         pass
#     
#     def add_contract(contract):
#         pass
#     
#     def update_contract(contract):
#         pass
    
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
    
class Ship:
    def __init__(self,ship_dict):
        self._symbol = ship_dict["symbol"]
        registration = ship_dict["registration"]
        self._faction_symbol = registration["factionSymbol"]
        self._role = registration["role"]
        
        self._navigation = self.Navigation(ship_dict["nav"])
        self._crew = self.Crew(ship_dict["crew"])
        self._frame = self.Frame(ship_dict["frame"])
        self._reactor = self.Reactor(ship_dict["reactor"])
        self._engine = self.Engine(ship_dict["engine"])
        self._modules = []
        for module in ship_dict["modules"]:
            new_module = self.Module(module)
            self._modules.append(new_module)
        
        self._mounts = []
        for mount in ship_dict["mounts"]:
            new_mount = self.Mount(mount)
            self._mounts.append(new_mount)
        
        self._cargo = self.Cargo(ship_dict["cargo"])
        
        self._fuel = self.Fuel(ship_dict["fuel"])
        
        self._cooldown = self.Cooldown(ship_dict["cooldown"])


    class Navigation:
        def __init__(self,nav_dict):
            self._system_symbol = nav_dict["systemSymbol"]
            self._waypoint_symbol = nav_dict["waypointSymbol"]
            self._route = self.Route(nav_dict["route"])
            self._status = nav_dict["status"]
            self._flight_mode = nav_dict["flightMode"]
            
        class Route:
            def __init__(self,route_dict):
                pass
    
    class Crew:
        def __init__(self,crew_dict):
            self._current_count = crew_dict["current"]
            self._required_count = crew_dict["required"]
            self._capacity = crew_dict["capacity"]
            self._rotation = crew_dict["rotation"]
            self._morale = crew_dict["morale"]
            self._wages = crew_dict["wages"]
            
    class Frame:
        def __init__(self,frame_dict):
            self._symbol = frame_dict["symbol"]
            self._name = frame_dict["name"]
            self._condition = frame_dict["condition"]
            self._integrity = frame_dict["integrity"]
            self._description = frame_dict["description"]
            self._module_slots = frame_dict["moduleSlots"]
            self._mounting_points = frame_dict["mountingPoints"]
            self._fuel_capacity = frame_dict["fuelCapacity"]
            self._requirements = frame_dict["requirements"]
            self._quality = frame_dict["quality"]
            
    class Reactor:
        def __init__(self,reactor_dict):
            self._symbol = reactor_dict["symbol"]
            self._name = reactor_dict["name"]
            self._condition = reactor_dict["condition"]
            self._integrity = reactor_dict["integrity"]
            self._description = reactor_dict["description"]
            self._power_output = reactor_dict["powerOutput"]
            self._requirements = reactor_dict["requirements"]
            
    class Engine:
        def __init__(self,engine_dict):
            self._symbol = engine_dict["symbol"]
            self._name = engine_dict["name"]
            self._condition = engine_dict["condition"]
            self._integrity = engine_dict["integrity"]
            self._description = engine_dict["description"]
            self._speed = engine_dict["speed"]
            self._requirements = engine_dict["requirements"]
    
    class Module:
        def __init__(self,module_dict):
            self._symbol = module_dict["symbol"]
            self._name = module_dict["name"]
            self._description = module_dict["description"]
            self._requirements = module_dict["requirements"]
            self._capacity = None
            if "capacity" in module_dict:
                self._capacity = module_dict["capacity"]
                
    class Mount:
        def __init__(self,mount_dict):
            self._symbol = mount_dict["symbol"]
            self._name = mount_dict["name"]
            self._description = mount_dict["description"]
            self._requirements = mount_dict["requirements"]
            self._strength = mount_dict["strength"]
            
    class Cargo:
        def __init__(self,cargo_dict):
            self._capacity = cargo_dict["capacity"]
            self._units = cargo_dict["units"]
            self._inventory = cargo_dict["inventory"]
            
    class Fuel:
        def __init__(self,fuel_dict):
            self._current = fuel_dict["current"]
            self._capacity = fuel_dict["capacity"]
            self._consumed = fuel_dict["consumed"]
        
    class Cooldown:
        def __init__(self,cooldown_dict):
            self._total_seconds = cooldown_dict["totalSeconds"]
            self._remaining_seconds = cooldown_dict["remainingSeconds"]
            
    
def server_to_datetime(server_time):
    normal_time = datetime.datetime.fromisoformat(server_time)
    
    return normal_time
    
    

    

    
    
    
## test centre
if __name__ == "__main__":
    with open("AccountToken.txt") as account_file:
        account_token = account_file.read().strip()
        
    current_game = Game(account_token,DATABASE_NAME)

    with open("AgentToken.txt") as token_file:
        agent_token = token_file.read().strip()
        

    current_game.add_agent(agent_token)
    current_game.handle_requests()
    print(current_game.get_agents())
    

    