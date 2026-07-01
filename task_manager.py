from tasks.task1_reaction import Task1Reaction

class TaskManager:
    def __init__(self, modi_io, participant_id):
        self.modi_io = modi_io
        self.participant_id = participant_id

    def run_task1(self):
        task = Task1Reaction(self.modi_io, self.participant_id)
        task.run()