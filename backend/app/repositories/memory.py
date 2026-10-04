import collections
from typing import List, Optional, Any, Dict
from backend.app.repositories.interfaces import IEventRepository, IAlertRepository

class InMemoryEventRepository(IEventRepository):
    def __init__(self, max_capacity: int = 1000):
        self._max_capacity = max_capacity
        self._events: collections.OrderedDict[str, Any] = collections.OrderedDict()

    def add(self, event: Any) -> None:
        if hasattr(event, "event_id"):
            eid = event.event_id
        elif isinstance(event, dict) and "event_id" in event:
            eid = event["event_id"]
        else:
            return

        self._events[eid] = event
        self._events.move_to_end(eid)
        
        # Enforce bounded capacity
        while len(self._events) > self._max_capacity:
            self._events.popitem(last=False)

    def get(self, event_id: str) -> Optional[Any]:
        return self._events.get(event_id)

    def list(self, skip: int = 0, limit: int = 100, **filters) -> List[Any]:
        results = []
        for event in reversed(self._events.values()):
            match = True
            
            # Simple filtering
            if filters:
                for k, v in filters.items():
                    if v is None:
                        continue
                        
                    if hasattr(event, k):
                        if getattr(event, k) != v:
                            match = False
                            break
                    elif isinstance(event, dict) and k in event:
                        if event[k] != v:
                            match = False
                            break
                    else:
                        match = False
                        break
                        
            if match:
                results.append(event)
                
        # Return paginated
        return results[skip: skip + limit]

    def get_total_count(self, **filters) -> int:
        count = 0
        for event in self._events.values():
            match = True
            if filters:
                for k, v in filters.items():
                    if v is None: continue
                    if hasattr(event, k):
                        if getattr(event, k) != v: match = False; break
                    elif isinstance(event, dict) and k in event:
                        if event[k] != v: match = False; break
                    else:
                        match = False; break
            if match:
                count += 1
        return count

class InMemoryAlertRepository(IAlertRepository):
    def __init__(self, max_capacity: int = 500):
        self._max_capacity = max_capacity
        self._alerts: collections.OrderedDict[str, Any] = collections.OrderedDict()

    def add(self, alert: Any) -> None:
        self._alerts[alert.alert_id] = alert
        self._alerts.move_to_end(alert.alert_id)
        
        # Enforce bounded capacity
        while len(self._alerts) > self._max_capacity:
            self._alerts.popitem(last=False)

    def get(self, alert_id: str) -> Optional[Any]:
        return self._alerts.get(alert_id)

    def update(self, alert: Any) -> None:
        if alert.alert_id in self._alerts:
            self._alerts[alert.alert_id] = alert
            # keep the position

    def list(self, skip: int = 0, limit: int = 100, **filters) -> List[Any]:
        results = []
        # Return most recent first
        for alert in reversed(self._alerts.values()):
            match = True
            if filters:
                for k, v in filters.items():
                    if v is None:
                        continue
                    if hasattr(alert, k):
                        if getattr(alert, k) != v:
                            match = False
                            break
            if match:
                results.append(alert)
                
        return results[skip: skip + limit]

    def get_total_count(self, **filters) -> int:
        count = 0
        for alert in self._alerts.values():
            match = True
            if filters:
                for k, v in filters.items():
                    if v is None: continue
                    if hasattr(alert, k):
                        if getattr(alert, k) != v: match = False; break
            if match:
                count += 1
        return count

class InMemoryIncidentRepository:
    def __init__(self, max_capacity: int = 200):
        self._max_capacity = max_capacity
        self._incidents: collections.OrderedDict[str, Any] = collections.OrderedDict()

    def add(self, incident: Any) -> None:
        self._incidents[incident.id] = incident
        self._incidents.move_to_end(incident.id)
        while len(self._incidents) > self._max_capacity:
            self._incidents.popitem(last=False)

    def get(self, incident_id: str) -> Optional[Any]:
        return self._incidents.get(incident_id)

    def update(self, incident: Any) -> None:
        if incident.id in self._incidents:
            self._incidents[incident.id] = incident

    def list(self, skip: int = 0, limit: int = 100, **filters) -> List[Any]:
        results = []
        for incident in reversed(self._incidents.values()):
            match = True
            if filters:
                for k, v in filters.items():
                    if v is None: continue
                    if hasattr(incident, k):
                        if getattr(incident, k) != v: match = False; break
                    elif isinstance(incident, dict) and k in incident:
                        if incident[k] != v: match = False; break
                    else:
                        match = False; break
            if match:
                results.append(incident)
        return results[skip: skip + limit]

    def get_total_count(self, **filters) -> int:
        count = 0
        for incident in self._incidents.values():
            match = True
            if filters:
                for k, v in filters.items():
                    if v is None: continue
                    if hasattr(incident, k):
                        if getattr(incident, k) != v: match = False; break
                    elif isinstance(incident, dict) and k in incident:
                        if incident[k] != v: match = False; break
                    else:
                        match = False; break
            if match:
                count += 1
        return count
