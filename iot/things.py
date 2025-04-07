import ujson

class Thing:
    def __init__(self, name, description):
        self.name = name
        self.description = description
        self.properties = {}
        self.methods = {}

    def add_property(self, name, value_getter, description=""):
        self.properties[name] = {
            "getter": value_getter,
            "description": description
        }

    def add_method(self, name, callback, parameters=None, description=""):
        self.methods[name] = {
            "callback": callback,
            "parameters": parameters or {},
            "description": description
        }

    def get_descriptor_json(self):
        descriptor = {
            "name": self.name,
            "description": self.description,
            "properties": {
                name: {
                    "description": prop["description"],
                    "type": type(prop["getter"]()).__name__
                }
                for name, prop in self.properties.items()
            },
            "methods": {
                name: {
                    "description": method["description"],
                    "parameters": method["parameters"]
                }
                for name, method in self.methods.items()
            }
        }
        return ujson.dumps(descriptor)

    def get_state_json(self):
        state = {
            "name": self.name,
            "state": {
                name: prop["getter"]()
                for name, prop in self.properties.items()
            }
        }
        return ujson.dumps(state)

    def invoke(self, command):
        method_name = command.get("method")
        parameters = command.get("parameters", {})
        if method_name in self.methods:
            method = self.methods[method_name]
            for param_name, param_value in parameters.items():
                if param_name not in method["parameters"]:
                    raise ValueError(f"Unexpected parameter: {param_name}")
            method["callback"](parameters)
        else:
            raise ValueError(f"Method not found: {method_name}")


class ThingManager:
    def __init__(self):
        self.things = []
        self.last_states = {}

    def add_thing(self, thing):
        self.things.append(thing)

    def get_descriptors_json(self):
        descriptors = [ujson.loads(thing.get_descriptor_json()) for thing in self.things]
        return ujson.dumps(descriptors)

    def get_states_json(self, delta=False):
        states = []
        changed = False
        for thing in self.things:
            state = ujson.loads(thing.get_state_json())
            if delta:
                last_state = self.last_states.get(thing.name)
                if last_state == state:
                    continue
                changed = True
            self.last_states[thing.name] = state
            states.append(state)
        return ujson.dumps(states), changed

    def invoke(self, command):
        thing_name = command.get("name")
        for thing in self.things:
            if thing.name == thing_name:
                thing.invoke(command)
                return
        raise ValueError(f"Thing not found: {thing_name}")
