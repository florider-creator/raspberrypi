import sys
import time
import RPi.GPIO as GPIO
from wheels import Wheels, Direction
from ultrasonic import DistanceSensors
from servos import ServoDirection, ServoEnd

class AutoRobot:
    def __init__(self, scanInterval = 0.1):
        self.sensors = DistanceSensors()
        self.robot = Wheels()

        self.previousDistance = -1.0
        self.previousDirection = Direction.Stop
        self.stuckCount = 0

        # start distance scanning
        if not(self.sensors.StartScanner(scanInterval, True)):
            raise SensorException("Distance sensors not working")

    def GetDistanceToNextObstacle(self):
        '''
            Returns the remaining direction, distance in CMs in the current direction of travel
            Returns space in forward direction if stopped or rotating 
        '''
        distance = -1.0
        if self.robot.direction == Direction.Forward or self.robot.direction == Direction.Stop or \
            self.robot.direction == Direction.SpinLeft or self.robot.direction == Direction.SpinRight:
            distance = self.sensors.frontDistance[ServoDirection.Ahead]
        elif self.robot.direction == Direction.Reverse:
            distance = self.sensors.backDistance[ServoDirection.Ahead]
        elif self.robot.direction == Direction.ForwardRight:
            distance = self.sensors.frontDistance[ServoDirection.OffRight]
        elif self.robot.direction == Direction.ForwardLeft:
            distance = self.sensors.frontDistance[ServoDirection.OffLeft]
        elif self.robot.direction == Direction.ReverseLeft:
            distance = self.sensors.backDistance[ServoDirection.OffLeft]
        elif self.robot.direction == Direction.ReverseRight:
            distance = self.sensors.backDistance[ServoDirection.OffRight]
        elif self.robot.direction == Direction.MoveRight:
            distance = self.sensors.frontDistance[ServoDirection.Right]
        elif self.robot.direction == Direction.MoveLeft:
            distance = self.sensors.frontDistance[ServoDirection.Left]
        return self.robot.direction, distance

    def GetFurthestEnd(self):
        '''
            returns direction, distance
            Work out if there is more space infront or behind and ignore sides
        '''
        if self.sensors.backDistance[ServoDirection.Ahead] > self.sensors.frontDistance[ServoDirection.Ahead]:
            print("Furthest = Reverse", self.sensors.backDistance[ServoDirection.Ahead])
            return Direction.Reverse, self.sensors.backDistance[ServoDirection.Ahead]
        else:
            print("Furthest = Forward", self.sensors.frontDistance[ServoDirection.Ahead])
            return Direction.Forward, self.sensors.frontDistance[ServoDirection.Ahead]

    def GetMaxDistanceDirection(self):
        '''
            returns servo end, servo direction, distance
            Returns the sensor direction with the most space and what that distance is
        '''
        maxRearDistance = max(self.sensors.backDistance.values())
        maxFrontDistance = max(self.sensors.frontDistance.values())

        if maxRearDistance > maxFrontDistance:
            res = [key for key in self.sensors.backDistance if self.sensors.backDistance[key] >= maxRearDistance]
            return ServoEnd.Back, res[0], maxRearDistance
        else:
            res = [key for key in self.sensors.frontDistance if self.sensors.frontDistance[key] >= maxFrontDistance]
            return ServoEnd.Front, res[0], maxFrontDistance
            return Direction.Forward, self.sensors.frontDistance[ServoDirection.Ahead]

    def GetMinDistanceDirection(self):
        '''
            returns servo end, servo direction, distance
            Returns the sensor direction with the most space and what that distance is
        '''
        minRearDistance = min(self.sensors.backDistance.values())
        minFrontDistance = min(self.sensors.frontDistance.values())

        if minRearDistance < minFrontDistance:
            res = [key for key in self.sensors.backDistance if self.sensors.backDistance[key] <= minRearDistance]
            return ServoEnd.Back, res[0], minRearDistance
        else:
            res = [key for key in self.sensors.frontDistance if self.sensors.frontDistance[key] <= minFrontDistance]
            return ServoEnd.Front, res[0], minFrontDistance

    def SetSpeedBasedOnDistance(self, distance):
        '''
        set speed based on space infront of us
        return the current speed
        '''
        if distance < 20.0:
            self.robot.Stop()
        elif distance < 40.0:
            self.robot.Speed(40)
        elif distance < 60.0:
            self.robot.Speed(50)
        elif distance < 100.0:
            self.robot.Speed(80) 
        else:
            self.robot.Speed(100) 
        return self.robot.robotspeed

    def RotateToBiggestSpace(self):
        ''' 
            returns direction, distance in new direction of travel
            Rotates so either front or rear is pointing to biggests space.
        '''
        attempts = 5
        while attempts > 0: # repeat until the front or back is pointing to the biggest space
            preferredDirection = self.GetMaxDistanceDirection()
            print("rotating, preferred direction is ", preferredDirection)

            self.robot.Speed(70)
            
            # work out whether to spin right or left
            if (preferredDirection[0] == ServoEnd.Front and 
                (preferredDirection[1] == ServoDirection.OffRight or preferredDirection[1] == ServoDirection.Right)) or \
                (preferredDirection[0] == ServoEnd.Back and 
                (preferredDirection[1] == ServoDirection.OffLeft or preferredDirection[1] == ServoDirection.Left)):
                self.robot.SpinRight()
                print("spin right")
            else:
                self.robot.SpinLeft()
                print("spin left")

            if ServoDirection.OffLeft or ServoDirection.OffRight:
                time.sleep(0.5) # rotate 45 degrees
            else: 
                time.sleep(1.0) # rotate 90 degrees
            self.robot.Stop()

            preferredDirection = self.GetMaxDistanceDirection()
            
            # if the best direction is forward or reverse don't spin and return
            if preferredDirection[1] == ServoDirection.Ahead or \
                preferredDirection[1] == ServoDirection.OffLeft or \
                preferredDirection[1] == ServoDirection.OffRight:
                print("direction chosen", preferredDirection[0], preferredDirection[1], preferredDirection[2])
                if preferredDirection[0] == ServoEnd.Front:
                    return Direction.Forward, preferredDirection[2]
                else:
                    return Direction.Reverse, preferredDirection[2]

            # wait to get new set of distance readings
            time.sleep(1)
            attempts -= 1
        raise StuckExcepion("cannot rotate out of trouble giving up")

    def AreWeStuck(self, direction, distance):
        '''
        returns True if we haven't moved since the last scan
        '''
        if abs(distance - self.previousDistance) < 1.0 and direction == self.previousDirection and direction != Direction.Stop:
            self.stuckCount += 1
            if self.stuckCount == 4:
                print("Stuck!")
                return True
        else:
            self.stuckCount = 0
        return False

    def UpdatePosition(self, direction, distance):
        '''
            Record our current location we we can determine later if we are stuck
        '''
        self.previousDirection = direction
        self.previousDistance = distance

    def GetNearestObstacleInDirectionOfTravel(self, currentDirection):
        '''
        Find out how far away we are from any obstacle directly infront of our direction of travel
        '''
        nearestObstacle = autonomousRobot.GetMinDistanceDirection()
        if nearestObstacle[0] == ServoEnd.Front:
            obstacleGeneralDirection = Direction.Forward
        else:
            obstacleGeneralDirection = Direction.Reverse
        if obstacleGeneralDirection != currentDirection:
            return 1000.0
        return nearestObstacle[2]

GPIO.setmode(GPIO.BCM)
autonomousRobot = AutoRobot(0.1)
time.sleep(1) # allow sensors time to complete a scan

try:
    # work out if we want to go forwards or backwards based on available space
    currentDirection = autonomousRobot.GetFurthestEnd()
    
    # if we have less than 10 cm left in our preferred direction see if another direction would be better
    if currentDirection[1] < 20.0:
        currentDirection = autonomousRobot.RotateToBiggestSpace()

    autonomousRobot.SetSpeedBasedOnDistance(currentDirection[1])
    autonomousRobot.robot.Move(currentDirection[0])
    loop = 1

    while True:
        currentDirection = autonomousRobot.GetDistanceToNextObstacle()
        nearestObstacle = autonomousRobot.GetNearestObstacleInDirectionOfTravel(currentDirection[0])

        # display current metrics every 4th loop
        loop -= 1
        if loop == 0:
            loop = 4
            print(currentDirection, nearestObstacle)

        # adjust speed as we move relative to any obstacles in front of us, factor in any obstacles to the side
        # take the average distance between nearest front obstacle and side obstacle if the nearest obstacle isn't directly infront of us
        speedDistance = min(currentDirection[1], (nearestObstacle + currentDirection[1]) / 2)
        autonomousRobot.SetSpeedBasedOnDistance(speedDistance)

        # change direction if:
        # there is less than 25cm left in direction of travel  
        # or there is an obstacle anywhere infront of us < 10cm
        # or we haven't made forward progress since the last scan
        if currentDirection[1] < 25.0 or nearestObstacle < 10.0 or autonomousRobot.AreWeStuck(currentDirection[0], currentDirection[1]): 
            currentDirection = autonomousRobot.RotateToBiggestSpace()
            autonomousRobot.SetSpeedBasedOnDistance(currentDirection[1])
            autonomousRobot.robot.Move(currentDirection[0])

        autonomousRobot.UpdatePosition(currentDirection[0], currentDirection[1])
        time.sleep(0.6)

finally:
    autonomousRobot.robot.Stop()
    autonomousRobot.sensors.StopScanner()
    GPIO.cleanup()