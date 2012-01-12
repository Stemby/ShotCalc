#!/usr/bin/env python

#    ShotCalc
#    Copyright (C) 2012, Carlo Stemberger
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Software for programming camera placement and settings in stop motion shots.

Movements: pan, tilt, dolly, pedestal, etc.
Settings: focus, etc.
"""

import numpy as np
from scipy.interpolate.polyint import pchip

class Camera(object):

    def __init__(self, framerate, movements):
        self.framerate = framerate
        self.movements = movements
        self.steps = {}

    def add_step(self, frame, values):
        """Add a new step.

        'frame' can be:
         the timecode string (e.g. '00:01:43:07'), or
         the frame number (e.g. 28, corresponting to '00:00:01:04' at 24 FPS)
        """
        self.steps[TimeCode(self.framerate, frame)] = values

    def find_positions(self):
        """Yield the position for each movement, frame by frame."""
        values = {}
        for movement in self.movements:
            steps = []
            for timecode in self.steps:
                if movement in self.steps.get(timecode):
                    steps.append((int(timecode),
                        self.steps[timecode][movement]))
                    steps.sort()
            values[movement] = interpolate(steps)
        for frame in range(min(self.steps), max(self.steps) + 1):
            yield (frame, dict((movement, func(frame)) for movement,
                        func in values.iteritems()))


class TimeCode(object):

    """A TimeCode object.

    'framerate' is an integer such as 24, that means 24 FPS;
    'frame' can be:
     the timecode string (e.g. '00:01:43:07'), or
     the frame number (e.g. 28, corresponting to '00:00:01:04' at 24 FPS)
    """

    def __init__(self, framerate, frame):
        self.framerate = framerate

        if isinstance(frame, str): 
            self.timecode = frame
        else:
            hh = 0
            mm = 0
            ss = 0
            fr = frame 
            if fr >= framerate:
                ss, fr = divmod(fr, framerate)
            mm, ss = divmod(ss, 60)
            hh, mm = divmod(mm, 60)
            while hh >= 24:
                hh = hh % 24
            self.timecode = '{:02}:{:02}:{:02}:{:02}'.format(hh, mm, ss, fr)

        hh, mm, ss, fr = map(int, self.timecode.split(':'))
        self.fnumber = (
                hh * 60 * 60 * framerate +
                mm * 60 * framerate +
                ss * framerate
                + fr)

    def __repr__(self):
        return "<TimeCode object ('{}')>".format(self.timecode)

    def __str__(self):
        return self.timecode

    def __lt__(self, other):
        return self.fnumber < other.fnumber

    def __le__(self, other):
        return self.fnumber <= other.fnumber

    def __eq__(self, other):
        return self.fnumber == other.fnumber

    def __ne__(self, other):
        return self.fnumber != other.fnumber

    def __gt__(self, other):
        return self.fnumber > other.fnumber

    def __ge__(self, other):
        return self.fnumber >= other.fnumber

    def __add__(self, other):
        return self.fnumber + other

    def __sub__(self, other):
        return self.fnumber - other

    def __int__(self):
        return self.fnumber


def interpolate(steps, smooth_start=True, smooth_stop=True):
    """Return a smooth curve through the steps."""
    # TODO: not only smooth start and stop (cut)
    # TODO: add "follow" (not programmed) movement
    x = np.array([step[0] for step in steps])
    y = np.array([step[1] for step in steps], float)
    func = pchip(x, y)
    
    # NOTE: debugging code
    import matplotlib.pyplot as plt
    xnew = np.linspace(x[0], x[-1], (x[-1] - x[0]) // 10)
    plt.plot(x, y, '-', xnew, func(xnew), 'o')
    plt.show()

    return func 

if __name__ == '__main__':
    # TODO: run a Qt GUI

    c = Camera(24, ['dolly', 'pan', 'tilt'])
    c.add_step(32, {'dolly': 35, 'pan': 60, 'tilt': 15})
    c.add_step('00:00:07:00', {'dolly': 375})
    c.add_step('00:00:10:00', {'dolly': 400, 'pan': 90, 'tilt': 0})

    prova = c.find_positions()
    print prova.next()
    print prova.next()

