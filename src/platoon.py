import logging
import traci
import random


class Route():

    def __init__(self, vehicle):
        self.vehicle = vehicle
        self.route = traci.vehicle.getRoute(vehicle)
        self.destination = self.route[-1]

    def getRemainingRoute(self):
        return self.route[traci.vehicle.getRouteIndex(self.vehicle):]


class Platoon():

    def __init__(self, startingVehicles):
        """Create a platoon, setting default values for all variables"""
        logging.info("Creating a new platoon with: %s", startingVehicles)
        self._active = True
        self._leadVehicle = startingVehicles[0]  # must be better than this
        self._lane = traci.vehicle.getLaneID(self._leadVehicle)
        self._lanePosition = traci.vehicle.getLanePosition(self._leadVehicle)
        self._vehicles = set(startingVehicles)
        self._routes = [Route(v) for v in startingVehicles]
        self._platoonCutOff = None
        self._color = (random.randint(0, 255), random.randint(
            0, 255), random.randint(0, 255))
        self.startPlatoonBehaviour(startingVehicles)

    def addVehicleToPlatoon(self, vehicle):
        """Adds a single vehicle to this platoon"""
        self._vehicles.add(vehicle)
        self.startPlatoonBehaviour([vehicle, ])
        self._routes.append(Route(vehicle))
        logging.info("Adding %s to platoon %s, New length: %s",
                     vehicle, self.getPlatoonID(), len(self._vehicles))

    def disbandPlatoon(self):
        """Marks a platoon as dead and returns vehicles to normal"""
        self.stopPlatoonBehvaviour()
        self._active = False
        logging.info("Disbanding platoon: %s", self.getPlatoonID())

    def getAllVehicles(self):
        """Retrieve the list of all the vehicles in this platoon"""
        return self._vehicles

    def getPlatoonID(self):
        """Generates and returns a unique ID for this platoon"""
        return "%s" % (self._leadVehicle)

    def isActive(self):
        """Is the platoon currently active within the scenario"""
        return self._active

    def mergePlatoon(self, platoon):
        """Merges the given platoon into the current platoon"""
        if self.checkVehiclePathsConverge(platoon.getAllVehicles()):
            platoon.disbandPlatoon()
            for vehicle in platoon.getAllVehicles():
                self.addVehicleToPlatoon(vehicle)
            return True
        else:
            logging.error("Could not merge platoon %s with platoon %s",
                          platoon.getPlatoonID(), self.getPlatoonID())
            return False

    def startPlatoonBehaviour(self, vehicles):
        """A function to start platooning a specific set of vehicles"""
        if self.isActive():
            for vehicle in vehicles:
                traci.vehicle.setColor(vehicle, self._color)
                traci.vehicle.setTau(vehicle, 0.05)
                traci.vehicle.setSpeedFactor(vehicle, 1)
                traci.vehicle.setMinGap(vehicle, 0)
                traci.vehicle.setImperfection(vehicle, 0)
        self.updatePlatoon()

    def stopPlatoonBehvaviour(self):
        """Stops vehicles exhibiting platoon behaviour, if they are
        still present within the map"""
        vehicleList = traci.vehicle.getIDList()
        for vehicle in self._vehicles:
            if vehicle in vehicleList:
                traci.vehicle.setSpeed(vehicle, -1)
                traci.vehicle.setColor(vehicle, (255, 255, 255))
                traci.vehicle.setTau(vehicle, 1)
                traci.vehicle.setSpeedFactor(vehicle, 0.9)
                traci.vehicle.setMinGap(vehicle, 2.5)
                traci.vehicle.setImperfection(vehicle, 0.5)

    def checkVehiclePathsConverge(self, vehicles):
        # Check that the given vehicles are going to follow the lead
        # vehicle into the next edge
        leadVehicleRoute = self._routes[0].getRemainingRoute()
        if len(leadVehicleRoute) > 1:
            leadVehicleNextEdge = leadVehicleRoute[1]
            for vehicle in vehicles:
                if leadVehicleNextEdge not in traci.vehicle.getRoute(vehicle):
                    return False
        return True

    def updatePlatoon(self):
        """Performs updates to maintain the platoon
        1. set platoon location information using lead vehicle
        2. set the speed of all vehicles in the convoy,
           using the lead vehicle's current speed
        3. is this platoon still alive (in the map),
           should it be labelled as inactive?"""

        # Location Info Update
        vehicleList = traci.vehicle.getIDList()
        leadInMap = self._leadVehicle in vehicleList

        self._lane = traci.vehicle.getLaneID(
            self._leadVehicle) if leadInMap else None
        self._lanePosition = traci.vehicle.getLanePosition(
            self._leadVehicle) if leadInMap else None

        if leadInMap:
            # Speed Update
            self.updatePlatoonSpeed(
                traci.vehicle.getSpeed(self._leadVehicle), False)

            # Route updates
            # Check that all cars still want to continue onto the
            # next edge, otherwise disband the platoon
            routeok = self.checkVehiclePathsConverge(self.getAllVehicles())
            if not routeok:
                self.disbandPlatoon()

        # Is Active Update
        if any([v not in vehicleList for v in self._vehicles]):
            self.disbandPlatoon()

    def updatePlatoonSpeed(self, speed, inclLeadingVeh=True):
        """ Sets the speed of all vehicles in the platoon
            If inclLeadingVeh set to false, then the leading vehicle is
            excluded from the speed change.
            Also checks that the platoon is bunched together, this allows
            for vehicles to "catch-up"
        """
        if not inclLeadingVeh:
            vehicles = self._vehicles - set([self._leadVehicle])
        else:
            vehicles = self.getAllVehicles()
        for veh in vehicles:
            leadVeh = traci.vehicle.getLeader(veh, 100)
            if leadVeh and leadVeh[1] <= 10:
                traci.vehicle.setSpeed(veh, speed)
