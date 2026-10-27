import http.client
import json
import sqlite3
import datetime
import os

DATABASE_NAME = "SpaceTraderDB.db"

class Game:
    def __init__(self,account_token,database_name):
        self._request_queue = []
        self._response_notify_list = []
        self._connection = http.client.HTTPSConnection("api.spacetraders.io")
        self._account_token = account_token
        self.request_status()
        if not self.handle_requests():
            print("failed to initiate game")
            return

        self._database = Database(database_name,self._last_reset)
        self._agents = []
        
        self._contracts = []
        
        for agent in self._database.get_agents():
            new_agent = Agent(self,agent_tuple=agent)
            self._agents.append(new_agent)
        self._current_agent = None
        
        
    def _announce_request(self,name):
        for function in self._response_notify_list:
            function(name)
            
    def add_listener(self,callback):
        self._response_notify_list.append(callback)
        
    def get_agents(self):
        if len(self._agents) == 0:
            agent_list = self._database.get_agents()
            for agent in agent_list:
                print(agent)
        return self._agents
    
    def register_agent(self,symbol=None,faction=None,response=None,):
        if response == None:
            payload_dict = {}
            payload_dict["symbol"] = symbol
            payload_dict["faction"] = faction
            payload = json.dumps(payload_dict)
            headers = {"Content-Type": "application/json",
                       "Authorization": f"Bearer {self._account_token}"}
            new_request = Request("POST","/v2/register",payload,headers,self.register_agent)
            self._request_queue.append(new_request)
        else:
            data = response["data"]
            new_token = data["token"]
            fake_response = {}
            fake_response["data"] = data["agent"]
            fake_response["data"]["token"] = new_token
            new_agent = self.add_agent(response=fake_response)
            
            fake_response = {}
            fake_response["data"] = data["ships"]
            new_agent.request_ships(fake_response)
            
            fake_response = {}
            fake_response["data"] = [data["contract"]]
            new_agent.request_contracts(fake_response)
            
        
    def add_agent(self,agent_token=None,response=None):
        if agent_token:
            headers = {"Authorization":f"Bearer {agent_token}"}
            new_request = Request("GET","/v2/my/agent",headers=headers,after=self.add_agent,descriptor="agent")
            self._request_queue.append(new_request)
        if response:
            if agent_token:
                response["data"]["token"] = agent_token
            new_agent = Agent(self,response["data"])
            command = """
                SELECT * FROM Agents
                WHERE Token = ?
                """
            if len(list(self._database.execute(command,new_agent.get_token()))) < 1:
                command = """
                    INSERT INTO Agents
                    VALUES (?,?)
                    """
                self._agents.append(new_agent)
                self._database.execute(command,new_agent.get_symbol(),new_agent.get_token())
                self.select_agent(new_agent)
            return new_agent
    
    def select_agent(self,agent):
        self._current_agent = agent
        self._current_agent.request_update()
        
    
    def get_current_agent(self):
        return self._current_agent
    
    def request_status(self,response=None):
        if response == None:
            token = self._account_token
            if token == None:
                print("no token")
                return
            headers = {"Authorization":f"Bearer {token}"}
            new_request = Request("GET","/v2/",headers=headers,after=self.request_status,descriptor="status")
            self.add_request(new_request)
            return
        
        self._status = response["status"]
        self._api_version = response["version"]
        self._last_reset = server_to_datetime(response["resetDate"])
        self._next_reset = server_to_datetime(response["serverResets"]["next"])
        
    
    def get_waypoints(self):
        pass
    
    def add_request(self,new_request):
        if isinstance(new_request,Request):
            self._request_queue.append(new_request)
    
    def handle_requests(self):
        if len(self._request_queue) < 1:
            return
        current_request = self._request_queue.pop(0)
        if current_request.command == "GET":
            self._connection.request(current_request.command,current_request.link,headers=current_request.headers)
        else:
            self._connection.request(current_request.command,current_request.link,current_request.payload,current_request.headers)
            
        response = self._connection.getresponse()
        response_headers = response.getheaders()
        response_data = response.read()
        
        if response.status < 200 or response.status >= 300:
            print("bad status: ",response.status)
            print(response_data)
            return
        if current_request.after == None:
            print(response_data)
            return
        
        response_json = json.loads(response_data) 
        current_request.after(response=response_json)
        descriptor = current_request.descriptor
        if descriptor and descriptor != "hidden":
            self._announce_request(descriptor)
            
        return True # truth as in success
                
        
    
class Request:
    def __init__(self,command,link,payload=None,headers=None,after=None,descriptor=None):
        self.command = command
        self.link = link
        self.payload = payload
        self.headers = headers
        self.after = after
        self.descriptor = descriptor

class Agent:
    def __init__(self,game,agent_dict=None,agent_tuple=None):
        self._game = game
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
            
        self._ships = {}
        
    def __repr__(self):
        return f"Agent-{self._symbol}"
    
    def request_update(self,response=None):
        if response == None:
            token = self.get_token()
            if token == None:
                print("no token")
                return
            headers = {"Authorization":f"Bearer {token}"}
            new_request = Request("GET","/v2/my/agent",headers=headers,after=self.request_update,descriptor="agent")
            self._game.add_request(new_request)
            self.request_ships()
            self.request_contracts()
        else:
            data = response["data"]
            self._symbol = data["symbol"]
            self._headquarters = data["headquarters"]
            self._credits = data["credits"]
            self._starting_faction = data["startingFaction"]
            self._ship_count = data["shipCount"]
    
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
    
    def get_loaded_ship_count(self):
        return len(self._ships)
    
    def get_ships(self):
        return self._ships
    
    def request_ships(self,response=None):
        if response == None:
            token = self.get_token()
            headers = {"Authorization":f"Bearer {token}"}
            new_request = Request("GET","/v2/my/ships",headers=headers,after=self.request_ships,descriptor="ships")
            self._game.add_request(new_request)
        else:
            ships_list = response["data"]
            for ship_dict in ships_list:
                symbol = ship_dict["symbol"]
                if symbol in self._ships:
                    self._ships[symbol].update(ship_dict)
                else:
                    new_ship = Ship(self,ship_dict)
                    self._ships[symbol] = new_ship
                
    def get_contracts(self,filter_type=None):
        return self._contracts
            
    def request_contracts(self,response=None):
        if response == None:
            token = self.get_token()
            headers = {"Authorization":f"Bearer {token}"}
            new_request = Request("GET","/v2/my/contracts",headers=headers,after=self.request_contracts,descriptor="contracts")
            self._game.add_request(new_request)
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

class Database:
    def __init__(self,database_name,last_reset_datetime):
        self._database_name = database_name
        ## check if stored data is expired ##
        last_modified_datetime = datetime.datetime.fromtimestamp(os.stat(DATABASE_NAME).st_mtime)
        if last_modified_datetime < last_reset_datetime:
            if os.path.exists(database_name):
                os.remove(database_name)
                print("reset old database")
        
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
    def __init__(self,owner,ship_dict):
        self._owner = owner
        self._symbol = ship_dict["symbol"]
        registration = ship_dict["registration"]
        self._faction_symbol = registration["factionSymbol"]
        self._role = registration["role"]
        self.update(ship_dict)

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
            
    def update(self,ship_dict):
        self._navigation = self.Navigation(ship_dict["nav"])
        self._crew = self.Crew(ship_dict["crew"])
        self._frame = self.Frame(ship_dict["frame"])
        self._reactor = self.Reactor(ship_dict["reactor"])
        self._engine = self.Engine(ship_dict["engine"])
        self._modules = {}
        for module in ship_dict["modules"]:
            symbol = module["symbol"]
            if symbol in self._modules:
                pass ## modules don't change?
            else:
                new_module = self.Module(module)
                self._modules[symbol] = new_module
        
        self._mounts = {}
        for mount in ship_dict["mounts"]:
            symbol = mount["symbol"]
            if symbol in self._mounts:
                pass ## mounts don't change?
            else:
                new_mount = self.Mount(mount)
                self._mounts[symbol] = new_mount
        
        self._cargo = self.Cargo(ship_dict["cargo"])
        
        self._fuel = self.Fuel(ship_dict["fuel"])
        
        self._cooldown = self.Cooldown(ship_dict["cooldown"])
        
    def can_chart(self):
        return True
    
    def chart(self,response=None):
        if response == None:
            if not self.can_chart():
                return
            
            token = self._owner.get_token()
            headers = {"Authorization":f"Bearer {token}"}
            url = "/v2/my/ships/" + self.get_symbol() + "/chart"
            new_request = Request("POST",url,headers=headers,after=self.chart,descriptor="chart")
            self._game.add_request(new_request)
        else:
            pass
        
        
    def can_negotiate_contract(self):
        # have no ongoing or offered contracts
        # must be at any waypoint with a faction present
        return True
    
    def negotiate_contract(self,response=None):
        if response == None:
            if not self.can_negotiate_contract():
                return
            token = self._owner.get_token()
            headers = {"Authorization":f"Bearer {token}"}
            url = "/v2/my/ships/" + self.get_symbol() + "/negotiate/contract"
            new_request = Request("POST",url,headers=headers,after=self.negotiate_contract,descriptor="contract")
            self._game.add_request(new_request)
        else:
            pass
        
    def can_dock(self):
        return True
    
    def dock(self,response=None):
        if request == None:
            if not self.can_dock():
                return
            token = self._owner.get_token()
            headers = {"Authorization":f"Bearer {token}"}
            url = "/v2/my/ships/" + self.get_symbol() + "/dock"
            new_request = Request("POST",url,headers=headers,after=self.dock,descriptor="ship")
            self._game.add_request(new_request)
        else:
            pass
        
    def can_extract(self):
        return True
    
    def extract(self,response=None,survey=None):
        if request == None:
            if not self.can_extract():
                return
            token = self._owner.get_token()
            headers = {"Authorization":f"Bearer {token}"}
            if survey:
                headers["Content-Type"] = "application/json"
                payload = json.dumps({})
                url = "/v2/my/ships/" + self.get_symbol() + "/extract/survey"
                new_request = Request("POST",url,payload,headers=headers,after=self.extract,descriptor="ship")
            else:
                url = "/v2/my/ships/" + self.get_symbol() + "/extract"
                new_request = Request("POST",url,headers=headers,after=self.extract,descriptor="ship")
            
            self._game.add_request(new_request)
        else:
            pass
        
    def can_jettison(self,good_symbol=None,amount=None):
        # check if got required goods to jettision before wasting request
        return True
    
    def jettison(self,good_symbol=None,amount=None,response=None):
        if response:
            if not self.can_jettison(good_symbol,amount):
                return
            token = self._owner.get_token()
            payload = json.dumps({})
            headers = {"Authorization":f"Bearer {token}",
                       "Content-Type":"application/json"}
            url = "/v2/my/ships/" + self.get_symbol() + "/jettison"
            new_request = Request("POST",url,payload,headers=headers,after=self.jettison,descriptor="ship")
            self._game.add_request(new_request)
        
        else:
            pass
    
    def can_jump(self,destination=None):
        # must have 1 antimatter
        # must be in orbit
        # must be to connected waypoint
        return True
    
    def jump(self,destination=None,response=None):
        if request == None:
            if not self.can_jump(destination):
                return
            token = self._owner.get_token()
            payload = json.dumps({"waypointSymbol":destination})
            headers = {"Authorization":f"Bearer {token}",
                       "Content-Type": "applications/json"}
            url = "/v2/my/ships/" + self.get_symbol() + "/jump"
            new_request = Request("POST",url,payload,headers=headers,after=self.jump,descriptor="ship")
            self._game.add_request(new_request)
        else:
            pass
        
    def can_scan(self):
        # must have a sensor array
        return True
    
    def scan(self,target=None,response=None):
        if response == None:
            if not self.can_scan():
                return
            token = self._owner.get_token()
            headers = {"Authorization":f"Bearer {token}"}
            match target:
                case "systems":
                    url = "/v2/my/ships/" + self.get_symbol() + "/scan/systems"
                case "waypoints":
                    url = "/v2/my/ships/" + self.get_symbol() + "/scan/waypoints"
                case "ships":
                    url = "/v2/my/ships/" + self.get_symbol() + "/scan/ships"
            
            new_request = Request("POST",url,headers=headers,after=self.scan,descriptor="galaxy")
            self._game.add_request(new_request)
        else:
            pass
        
    def can_scrap(self):
        # i function therefore I scrap
        # oh also needs to be at a shipyard
        return True
    
    def scrap(self,response=None):
        if response == None:
            if not self.can_scrap():
                return
            token = self._owner.get_token()
            headers = {"Authorization":f"Bearer {token}"}
            url = "/v2/my/ships/" + self.get_symbol() + "/scrap"
            new_request = Request("POST",url,headers=headers,after=self.scrap,descriptor="ship")
            self._game.add_request(new_request)
        else:
            pass
        
    def request_scrap_value(self,response=None):
        if response == None:
            token = self._owner.get_token()
            headers = {"Authorization":f"Bearer {token}"}
            url = "/v2/my/ships/" + self.get_symbol() + "/scrap"
            new_request = Request("GET",url,headers=headers,after=self.request_scrap_value,descriptor="ship")
            self._game.add_request(new_request)
        else:
            pass
            
    def request_ship_cooldown(self,request=None):
        if request == None:
            token = self._owner.get_token()
            headers = {"Authorization":f"Bearer {token}"}
            url = "/v2/my/ships/" + self.get_symbol() + "/cooldown"
            new_request = Request("GET",url,headers=headers,after=self.request_ship_cooldown,descriptor="ship")
            self._game.add_request(new_request)
        else:
            pass
        
    def can_navigate(self,destination=None):
        # must be in orbit
        return True
    
    def navigate(self,destination=None,response=None):
        if response == None:
            if not self.can_navigate():
                return
            token = self._owner.get_token()
            payload = json.dumps({"waypointSymbol":destination})
            headers = {"Authorization":f"Bearer {token}",
                       "Content-Type": "applications/json"}
            url = "/v2/my/ships/" + self.get_symbol() + "/navigate"
            new_request = Request("POST",url,payload,headers=headers,after=self.navigate,descriptor="ship")
            self._game.add_request(new_request)
        else:
            pass
        
    def can_warp(self,destination=None):
        # must be in orbit
        # must have warp drive
        return True
    
    def warp(self,destination=None,response=None):
        if response == None:
            if not self.can_warp():
                return
            token = self._owner.get_token()
            payload = json.dumps({"waypointSymbol":destination})
            headers = {"Authorization":f"Bearer {token}",
                       "Content-Type": "applications/json"}
            url = "/v2/my/ships/" + self.get_symbol() + "/warp"
            new_request = Request("POST",url,payload,headers=headers,after=self.warp,descriptor="ship")
            self._game.add_request(new_request)
        else:
            pass
        
    def can_orbit(self):
        return True
    
    def orbit(self,response=None):
        if response == None:
            if not self.can_orbit():
                return
            token = self._owner.get_token()
            headers = {"Authorization":f"Bearer {token}"}
            url = "/v2/my/ships/" + self.get_symbol() + "/orbit"
            new_request = Request("POST",url,headers=headers,after=self.orbit,descriptor="ship")
            self._game.add_request(new_request)
        else:
            pass
        
    def can_purchase_cargo(self,good_symbol=None,amount=None):
        ## must be docked at marketplace
        # market must be selling good_symbol
        # amount must be <= trade volume and > 0
        return True
    
    def purchase_cargo(self,good_symbol=None,amount=None,response=None):
        if response == None:
            if not self.can_purchase_cargo():
                return
            token = self._owner.get_token()
            payload = json.dumps({"symbol":good_symbol})
            headers = {"Authorization":f"Bearer {token}",
                       "Content-Type": "applications/json"}
            url = "/v2/my/ships/" + self.get_symbol() + "/purchase"
            new_request = Request("POST",url,payload,headers=headers,after=self.purchase_cargo,descriptor="ship")
            self._game.add_request(new_request)
        else:
            pass
        
    def can_refine(self,desired_symbol=None):
        # must have the raw version
        # have refinery module
        return True
    
    def refine(self,desired_symbol=None,response=None):
        if response == None:
            if not self.can_refine(desired_symbol):
                return
            token = self._owner.get_token()
            payload = json.dumps({"produce":desired_symbol})
            headers = {"Authorization":f"Bearer {token}",
                       "Content-Type": "applications/json"}
            url = "/v2/my/ships/" + self.get_symbol() + "/refine"
            new_request = Request("POST",url,payload,headers=headers,after=self.refine,descriptor="ship")
            self._game.add_request(new_request)
        else:
            pass
        
    def can_refuel(self):
        # must be at a marketplace
        # market must be selling fuel
        return True
    
    def refuel(self,amount=None,from_cargo=False,response=None):
        if response == None:
            if not self.can_refuel():
                return
            token = self._owner.get_token()
            payload = {}
            if amount:
                payload["units"] = amount
            payload["fromCargo"] = from_cargo
            payload = json.dumps(payload)
            headers = {"Authorization":f"Bearer {token}",
                       "Content-Type": "applications/json"}
            url = "/v2/my/ships/" + self.get_symbol() + "/refuel"
            new_request = Request("POST",url,payload,headers=headers,after=self.refuel,descriptor="ship")
            self._game.add_request(new_request)
        else:
            pass
            
    def can_repair(self):
        # must be docked at a shipyard
        return True
    
    def repair(self,response=None):
        if response == None:
            if not self.can_repair():
                return
            token = self._owner.get_token()
            headers = {"Authorization":f"Bearer {token}"}
            url = "/v2/my/ships/" + self.get_symbol() + "/repair"
            new_request = Request("POST",url,headers=headers,after=self.repair,descriptor="ship")
            self._game.add_request(new_request)
        else:
            pass
            
    def get_repair_cost(self,response=None):
        if response == None:
            if not self.can_repair():
                return
            token = self._owner.get_token()
            headers = {"Authorization":f"Bearer {token}"}
            url = "/v2/my/ships/" + self.get_symbol() + "/repair"
            new_request = Request("GET",url,headers=headers,after=self.get_repair_cost,descriptor="ship")
            self._game.add_request(new_request)
        else:
            pass
        
    def can_sell_cargo(self,good_symbol=None,amount=None):
        # must be docked at a marketplace
        # must have enough to sell
        return True
    
    def sell_cargo(self,good_symbol=None,amount=None,response=None):
        if response == None:
            if not self.can_sell_cargo():
                return
            token = self._owner.get_token()
            payload = {}
            payload["symbol"] = good_symbol
            payload["units"] = amount
            payload = json.dumps(payload)
            headers = {"Authorization":f"Bearer {token}",
                       "Content-Type": "applications/json"}
            url = "/v2/my/ships/" + self.get_symbol() + "/sell"
            new_request = Request("POST",url,payload,headers=headers,after=self.sell_cargo,descriptor="ship")
            self._game.add_request(new_request)
        else:
            pass
        
    def can_siphon(self):
        # must be in orbit of gas giant
        # must have siphon mounts
        # must have a gas processor
        return True
    
    def siphon(self,response=None):
        if response == None:
            if not self.can_siphon():
                return
            token = self._owner.get_token()
            headers = {"Authorization":f"Bearer {token}"}
            url = "/v2/my/ships/" + self.get_symbol() + "/siphon"
            new_request = Request("POST",url,headers=headers,after=self.siphon,descriptor="ship")
            self._game.add_request(new_request)
        else:
            pass
        
    def can_survey(self):
        # must have surveyor mount
        return True
    
    def survey(self,response=None):
        if response == None:
            if not self.can_survey():
                return
            token = self._owner.get_token()
            headers = {"Authorization":f"Bearer {token}"}
            url = "/v2/my/ships/" + self.get_symbol() + "/survey"
            new_request = Request("POST",url,headers=headers,after=self.survey,descriptor="survey")
            self._game.add_request(new_request)
        else:
            pass
        
    def can_transfer(self,good_symbol=None,amount=None,other_ship=None):
        # we must have enough
        # other ship must be in the same waypoint and has capacity
        # both must be in same state (both docked or both orbiting)
        return True
    
    def transfer(self,good_symbol=None,amount=None,other_ship=None,response=None):
        if response == None:
            if not self.can_transfer():
                return
            token = self._owner.get_token()
            payload = {}
            payload["tradeSymbol"] = good_symbol
            payload["units"] = amount
            payload["shipSymbol"] = other_ship.get_symbol()
            payload = json.dumps(payload)
            headers = {"Authorization":f"Bearer {token}",
                       "Content-Type": "applications/json"}
            url = "/v2/my/ships/" + self.get_symbol() + "/transfer"
            new_request = Request("POST",url,payload,headers=headers,after=self.transfer,descriptor="ship")
            self._game.add_request(new_request)
        else:
            pass
        
    def request_cargo(self,response=None):
        if response == None:
            token = self._owner.get_token()
            headers = {"Authorization":f"Bearer {token}"}
            url = "/v2/my/ships/" + self.get_symbol() + "/cargo"
            new_request = Request("GET",url,headers=headers,after=self.request_cargo,descriptor="ship")
            self._game.add_request(new_request)
        else:
            pass
        
    def request_modules(self,response=None):
        if response == None:
            token = self._owner.get_token()
            headers = {"Authorization":f"Bearer {token}"}
            url = "/v2/my/ships/" + self.get_symbol() + "/modules"
            new_request = Request("GET",url,headers=headers,after=self.request_modules,descriptor="ship")
            self._game.add_request(new_request)
        else:
            pass
        
    def can_install_module(self,module_symbol=None):
        # module must be in cargo
        return True
    
    def install_module(self,module_symbol=None,response=None):
        if response == None:
            if not self.can_install_module(module_symbol):
                return
            token = self._owner.get_token()
            payload = {}
            payload["symbol"] = module_symbol
            payload = json.dumps(payload)
            headers = {"Authorization":f"Bearer {token}",
                       "Content-Type": "applications/json"}
            url = "/v2/my/ships/" + self.get_symbol() + "/modules/install"
            new_request = Request("POST",url,payload,headers=headers,after=self.install_module,descriptor="ship")
            self._game.add_request(new_request)
        else:
            pass
        
    def can_remove_module(self,module_symbol=None):
        # must have given module installed
        # need room in cargo?
        return True
    
    def remove_module(self,module_symbol=None,response=None):
        if response == None:
            if not self.can_remove_module(module_symbol):
                return
            token = self._owner.get_token()
            payload = {}
            payload["symbol"] = module_symbol
            payload = json.dumps(payload)
            headers = {"Authorization":f"Bearer {token}",
                       "Content-Type": "applications/json"}
            url = "/v2/my/ships/" + self.get_symbol() + "/modules/remove"
            new_request = Request("POST",url,payload,headers=headers,after=self.remove_module,descriptor="ship")
            self._game.add_request(new_request)
        else:
            pass
            
    def request_mounts(self,response=None):
        if response == None:
            token = self._owner.get_token()
            headers = {"Authorization":f"Bearer {token}"}
            url = "/v2/my/ships/" + self.get_symbol() + "/mounts"
            new_request = Request("GET",url,headers=headers,after=self.request_mounts,descriptor="ship")
            self._game.add_request(new_request)
        else:
            pass
        
    def can_install_mount(self,mount_symbol=None):
        # mount must be in cargo
        # must be docked at a ship yard
        return True
    
    def install_mount(self,mount_symbol=None,response=None):
        if response == None:
            if not self.can_install_mount(mount_symbol):
                return
            token = self._owner.get_token()
            payload = {}
            payload["symbol"] = mount_symbol
            payload = json.dumps(payload)
            headers = {"Authorization":f"Bearer {token}",
                       "Content-Type": "applications/json"}
            url = "/v2/my/ships/" + self.get_symbol() + "/mounts/install"
            new_request = Request("POST",url,payload,headers=headers,after=self.install_mount,descriptor="ship")
            self._game.add_request(new_request)
        else:
            pass
        
    def can_remove_mount(self,mount_symbol=None):
        # must have given mount installed
        # must be docked at ship yard
        # need room in cargo?
        return True
    
    def remove_mount(self,mount_symbol=None,response=None):
        if response == None:
            if not self.can_remove_mount(mount_symbol):
                return
            token = self._owner.get_token()
            payload = {}
            payload["symbol"] = mount_symbol
            payload = json.dumps(payload)
            headers = {"Authorization":f"Bearer {token}",
                       "Content-Type": "applications/json"}
            url = "/v2/my/ships/" + self.get_symbol() + "/mounts/remove"
            new_request = Request("POST",url,payload,headers=headers,after=self.remove_mount,descriptor="ship")
            self._game.add_request(new_request)
            
        else:
            pass
        
    def request_nav(self,response=None):
        if response == None:
            token = self._owner.get_token()
            headers = {"Authorization":f"Bearer {token}"}
            url = "/v2/my/ships/" + self.get_symbol() + "/nav"
            new_request = Request("GET",url,headers=headers,after=self.request_nav,descriptor="ship")
            self._game.add_request(new_request)
        else:
            pass
        
    def patch_nav(self,flight_mode=None,response=None):
        if response == None:
            token = self._owner.get_token()
            payload = {}
            payload["flightMode"] = flight_mode
            payload = json.dumps(payload)
            headers = {"Authorization":f"Bearer {token}",
                       "Content-Type": "applications/json"}
            url = "/v2/my/ships/" + self.get_symbol() + "/nav"
            new_request = Request("PATCH",url,payload,headers=headers,after=self.patch_nav,descriptor="ship")
            self._game.add_request(new_request)
        else:
            pass
    
        
    def get_symbol(self):
        return self._symbol
            
    def get_faction(self):
        return self._faction_symbol
    
    def get_role(self):
        return self._role
    
def server_to_datetime(server_time):
    normal_time = datetime.datetime.fromisoformat(server_time)
    
    return normal_time
    
    

    

    
    
    
## test centre
if __name__ == "__main__":
    with open("AccountToken.txt") as account_file:
        account_token = account_file.read().strip()
        
    current_game = Game(account_token,DATABASE_NAME)



    
    

    