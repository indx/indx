#    This file is part of WebBox.
#
#    Copyright 2011-2012 Daniel Alexander Smith, Max Van Kleek
#    Copyright 2011-2012 University of Southampton
#
#    WebBox is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    WebBox is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with WebBox.  If not, see <http://www.gnu.org/licenses/>.

import logging, traceback, json
from twisted.web.resource import Resource
from webbox.webserver.handlers.base import BaseHandler
import webbox.webbox_pg2 as database
from webbox.objectstore_async import ObjectStoreAsync
import uuid

class EnrichHandler(BaseHandler):
    """ Add/remove boxes, add/remove users, change config. """
    base_path = 'enrich'
    
    def val(self, value):
        return {"@value": value}
    
    def get_next_round(self, request):
        token = self.get_token(request)
        if not token:
            return self.return_forbidden(request)
        store = token.store

        desc = request.args['desc'][0]
        user = ''
        owner = ''
        
        r = {
            "@id":              str(uuid.uuid1()),
            "type":             "round",
            "user":             None,
            "statement":        desc,
            "isOwn":            bool(owner == user)
        }
        
        place = self.try_to_find_entity(store, desc, 'places')
        if place is not None:
            r['place-start'] = place['start']
            r['place-end'] = place['end']
            r['place-full'] = place['full']
            r['place-abbrv'] = place['abbrv']
            
        establishment = self.try_to_find_entity(store, desc, 'establishments')
        if establishment is not None:
            r['establishment-start'] = establishment['start']
            r['establishment-end'] = establishment['end']
            r['establishment-full'] = establishment['full']
            r['establishment-abbrv'] = establishment['abbrv']
        
        self.return_ok(request, {"round": r})
        
    def save_entity_from_round(self, abbrv, full, table_name):
        entities = store.get_latest(table_name)
        found = False
        for entity_id, entity_info in entities :
            if (entity_id != "@version" and entity_id != "@graph"):
                if abbrv == entity_info["abbrv"][0]["@value"] and full == entity_info["full"][0]["@value"]:
                    entity_info["count"][0]["@value"] += 1
                    found = True
        if not found:
            entities.add(table_name, {"abbrv": abbrv, "full": full, "count": 1}, entities["@version"])

    def get_establishments(self, request):
        token = self.get_token(request)
        if not token:
            return self.return_forbidden(request)
        store = token.store
        
        # the highlighted string from user: "Kings X"
        q = request.args['q'][0]
        startswith = 'startswith' in request.args
        
        self.return_ok(request, {"entries": self.search_entity_for_term(store, q, "establishments", startswith)})


    def get_places(self, request):
        token = self.get_token(request)
        if not token:
            return self.return_forbidden(request)
        store = token.store
        
        # the highlighted string from user: "Kings X"
        q = request.args['q'][0]
        
        self.return_ok(request, {"entries": self.search_entity_for_term(store, q, "places")})
 
    def search_entity_for_term(self, store, term, table_name, startswith=False, approx=False):
        d = []
        entities = store.get_latest(table_name)
        for entity_id, entity_info in entities :
            if (entity_id != "@version" and entity_id != "@graph"):
                if approx:
                    if entity_info["abbrv"][0]["@value"].find(q, 0) > -1:
                        d.append({"id": entity_id, "name": entity_info["full"][0]["@value"]})
                elif startswith:
                    if entity_info["abbrv"][0]["@value"].startswith(q):
                        d.append({"id": entity_id, "name": entity_info["full"][0]["@value"], "count": entity_info["count"][0]["@value"]})
                else:
                    if entity_info["abbrv"][0]["@value"] == q:
                        d.append({"id": entity_id, "name": entity_info["full"][0]["@value"], "count": entity_info["count"][0]["@value"]})
        return d
        
    def try_to_find_entity(self, store, description, table_name):
        parts = description.split()
        
        candidates = []
        for sublist in self.iter_sublists(parts):
            abbrv = ' '.join(sublist)
            matches = self.search_entity_for_term(store, abbrv, table_name)
            if len(matches) > 0:
                for match in matches:
                    #if match not in candidates:
                    candidates.append({
                        'abbrv':    abbrv,
                        'start':    q.find(abbrv, 0),
                        'end':      q.find(abbrv, 0) + len(abbrv),
                        'full':     match['name'],
                        'count':    match['count']
                    })
        
        if len(candidates) > 0:
            return None
        else:
            candidates.sorted(candidates, self.sort_candidates)
            return candidates[0]
        
    def sort_candidates(self, a, b):
        if a['count'] == b['count']:
            return -1
        elif a['count'] > b['count']:
            return 1
        else:
            return -1
            
    def iter_sublists(self, l):
        n = len(l)+1
        for i in range(n):
            for j in range(i+1, n):
                yield l[i:j]
        
EnrichHandler.subhandlers = [
]
