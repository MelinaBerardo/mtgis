import time
from datetime import datetime
import statistics

class mtCallTimer:
    def __init__(self,name='timer'):
        self.last_call = time.perf_counter()
        self.last_process = time.process_time()
        self.name=name
        self.allLaps=[]
        self.allLapsProcess=[]

    def print_lap(self, message="Tick"):
        now = time.perf_counter()
        now_process=time.process_time()
        elapsed = now - self.last_call
        elapsed_process = now_process-self.last_process
        self.allLaps.append(elapsed)
        self.allLapsProcess.append(elapsed_process)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        print(f"[{self.name}][{timestamp}] {message} - Time since last call: {elapsed:.4f} seconds - process: {elapsed_process:.4f}")
        self.last_call = now
        self.last_process=now_process
    
    def start_lap(self):
        now = time.perf_counter()
        now_process=time.process_time()
        self.last_call = now
        self.last_process=now_process

    def mark_lap(self):
        now = time.perf_counter()
        now_process=time.process_time()
        elapsed = now - self.last_call
        elapsed_process = now_process-self.last_process
        self.allLaps.append(elapsed)
        self.allLapsProcess.append(elapsed_process)
        self.last_call = now
        self.last_process=now_process
    
    def print_stats(self):
        print(f"[{self.name}][Stats REAL: Max: {max(self.allLaps):.4f} Min: {min(self.allLaps):.4f} Avg: {statistics.mean(self.allLaps):.4f} Median: {statistics.median(self.allLaps):.4f} SD: {statistics.stdev(self.allLaps):.4f} Count: {len(self.allLaps)}")
        print(f"[{self.name}][Stats Proc: Max: {max(self.allLapsProcess):.4f} Min: {min(self.allLapsProcess):.4f} Avg: {statistics.mean(self.allLapsProcess):.4f} Median: {statistics.median(self.allLapsProcess):.4f} SD: {statistics.stdev(self.allLapsProcess):.4f} Count: {len(self.allLapsProcess)}")