import uuid


class ProgressTracker:
    def __init__(self, min=0, max=1, current=0, id=None):

        self.id = id
        self.max = max
        self.current = current
        self.min = min

    @property
    def complete(self):
        """
        Description:
            checks if the task is complete

        Return:
            [bool] True or False
        """
        
        if self.current >= self.max:
            return True
        return False

    @property
    def progress(self):
        """
        Description:
            calculates the progress
            
        Returns:
            [float] 0-1 value representing 0-100 percent.
        """
        
        if self.max:
            if self.current > 0:
                return float(self.current) / float(self.max)
            return 0.0

    def iterate(self, val=1):
        """
        Description: 
            increased the iteration counter
        """
        self.current += val


class ProgressHandler:
    def __init__(self):
        """
        Register queues so that a universal progress solver can feed a progressbar

        Returns:
            _type_: _description_
        """

        self.queue = {}
        self.incr = -1

        self.format = ""
        self.message = "Progress: "

    def tracker(self, id):
        return self.queue.get(id)

    def track_progress(self, items=1, id=None):
        tracker = ProgressTracker(max=items, id=id)
        self.queue[id] = tracker
        return tracker

    def iterate(self, id):
        self.queue.get(id).iterate()


    @property
    def progress(self):
        return sum([i.progress for i in self.queue.values()]) / float(len(self.queue))
