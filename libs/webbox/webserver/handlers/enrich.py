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

import logging, traceback, json, os
from twisted.web.resource import Resource
from twisted.internet.defer import Deferred

from webbox.webserver.handlers.base import BaseHandler
import webbox.webbox_pg2 as database
from webbox.objectstore_async import ObjectStoreAsync
import uuid
import random
import re

class EnrichHandler(BaseHandler):
    """ Add/remove boxes, add/remove users, change config. """
    base_path = 'enrich'
    
    def val(self, value):
        return {"@value": value}
    
    def get_unprocessed_statement(self, store, persona):
        result_d = Deferred()

        def get_graph(objs):
            keys = objs.keys()
            random.shuffle(keys)
            
            # get our objects
            for uri in keys:
                if uri[0] != "@":
                    obj = objs[uri]
                    logging.debug("object "+repr(obj))
                    if 'user' in obj and obj['user'][0]["@value"] == persona and ('place_id' not in obj or 'establishment_id' not in obj):
                        result_d.callback(obj)
                        return

            # get any object
            for uri in keys:
                if uri[0] != "@":
                    obj = objs[uri]
                    if ('place_id' not in obj or 'establishment_id' not in obj):
                        result_d.callback(obj)
                        return

            result_d.callback(None)

        store.get_latest("statements").addCallback(get_graph)

        return result_d


    def get_next_round(self, request):
        token = self.get_token(request)
        if not token:
            return self.return_forbidden(request)
        store = token.store

        persona = request.args['persona'][0]

        def got_statement(obj):
            if obj is None:
                return self.return_ok(request)
 
            user = persona
            owner = obj['user'][0]["@value"]
           
            if "field_cc_transaction_description" in obj:
                desc = obj['field_cc_transaction_description'][0]["@value"]
            elif "field_ba_transaction_description" in obj:
                desc = obj['field_ba_transaction_description'][0]["@value"]
            else:
                return self.return_internal_error(request)
                
            desc = re.sub(r"[0-2][0-9]:[0-5][0-9][A-Z][A-Z][A-Z][0-3][0-9]", "", desc, flags=re.I)
            desc = re.sub(r"[0-3][0-9][A-Z][A-Z][A-Z][0-9][0-9]", "", desc, flags=re.I)
            desc = re.sub(r"[A-Z][A-Z][A-Z][0-3][0-9]", "", desc, flags=re.I)
            desc = re.sub(r"[0-3][0-9][A-Z][A-Z][A-Z][0-3][0-9]", "", desc, flags=re.I)
            desc = re.sub(r"\+AEA-.*", "", desc, flags=re.I)
            desc = re.sub(r" +,+", ",", desc, flags=re.I)
            desc = re.sub(r" +", " ", desc, flags=re.I)
            desc = desc.strip()
        

            r = {
                "@id":              str(uuid.uuid1()),
                "type":             "round",
                "user":             user,
                "statement":        desc,
                "isOwn":            owner == user
            }
           
            def found_a(place):

                if place is not None:
                    r['place-start'] = place['start']
                    r['place-end'] = place['end']
                    r['place-full'] = place['full']
                    r['place-abbrv'] = place['abbrv']
                    
                def found_b(establishment):

                    if establishment is not None:
                        r['establishment-start'] = establishment['start']
                        r['establishment-end'] = establishment['end']
                        r['establishment-full'] = establishment['full']
                        r['establishment-abbrv'] = establishment['abbrv']
            
                    self.return_ok(request, {"round": r})


                self.try_to_find_entity(store, desc, 'establishments').addCallback(found_b)


            self.try_to_find_entity(store, desc, 'places').addCallback(found_a)
            

        self.get_unprocessed_statement(store, persona).addCallback(got_statement)

        
    def save_entity_from_round(self, abbrv, full, table_name, request, store):
       
        result_d = Deferred()
        
        def save_entities(entities):
            logging.debug('entities ' + repr(entities))
            
            new_entities = []
            
            found = False
            for entity_id, entity_info in entities.items():
                if entity_id[0] != "@":
                    if abbrv == entity_info["abbrv"][0]["@value"] and full == entity_info["full"][0]["@value"]:
                        entity_info["count"][0]["@value"] = str(int(entity_info["count"][0]["@value"]) + 1)
                        found = True
                    entity_info["@id"] = entity_id
                    new_entities.append(entity_info)

            if not found:
                id = str(uuid.uuid1())
                new_entity = {"@id": id, "abbrv": [{"@value":abbrv}], "full": [{"@value": full}], "count": [{"@value": "1"}]}
                new_entities.append(new_entity)

            def write_back(version_info):
                result_d.callback(None)
	    
            logging.debug("About to save entitites: "+repr(new_entities))
            store.add_graph_version(table_name, new_entities, entities["@version"][0]).addCallback(write_back)

        store.get_latest(table_name).addCallback(save_entities)
        return result_d

    def save_round(self, request):
        token = self.get_token(request)
        if not token:
            return self.return_forbidden(request)
        store = token.store

        logging.debug(' POST ARGS ' + repr(self.get_post_args(request)))

        r = json.loads(self.get_post_args(request)['round'][0]) # request.args['round'][0]
        logging.debug(' r ' + repr(r))
        
        def save_place(variable):
            if not (r["place-full"] == "_NOT_SPECIFIED_" or r["place-abbrv"] == "_NOT_SPECIFIED_"):
                self.save_entity_from_round(r["place-abbrv"], r["place-full"], "places", request, store).addCallback(lambda x: self.return_ok(request))
            else:
                self.return_ok(request)

     
        if not (r["establishment-full"] == "_NOT_SPECIFIED_" or r["establishment-abbrv"] == "_NOT_SPECIFIED_"):
            self.save_entity_from_round(r["establishment-abbrv"], r["establishment-full"], "establishments", request, store).addCallback(save_place)
        else:
            save_place(None)
            

    def get_establishments(self, request):
        token = self.get_token(request)
        if not token:
            return self.return_forbidden(request)
        store = token.store
        
        # the highlighted string from user: "Kings X"
        q = request.args['q'][0]
        startswith = 'startswith' in request.args
        
        def got_entities(returned):
            self.return_ok(request, {"entries": returned})

        self.search_entity_for_term(store, q, "establishments", startswith).addCallback(got_entities)


    def get_places(self, request):
        token = self.get_token(request)
        if not token:
            return self.return_forbidden(request)
        store = token.store
        
        # the highlighted string from user: "Kings X"
        q = request.args['q'][0]
        q = q.lower()
        startswith = 'startswith' in request.args
       
        def got_entities(returned):

            if len(returned) > 0:
                return self.return_ok(request, {"entries": returned})

            # else search the gazetteer
            f = open(os.path.join(os.path.dirname(__file__), "uk_places.json"), "r")
            uk_places = json.load(f)
            f.close()
            
            entities = []
            for place in uk_places:
                if startswith and place.lower().startswith(q):
                    entities.append(place)
                elif (not startswith) and place.lower() == q:
                    entities.append(place)
            return self.return_ok(request, {"entries": entities})
                

        self.search_entity_for_term(store, q, "places", startswith).addCallback(got_entities)


    def search_entity_for_term(self, store, q, table_name, startswith=False, approx=False):
        return_d = Deferred()
        q = q.lower()

        def got_latest(entities):
            d = []
            for entity_id, entity_info in entities.items():
                if entity_id[0] != "@":
                    if approx:
                        if entity_info["abbrv"][0]["@value"].lower().find(q, 0) > -1:
                            d.append({"id": entity_id, "name": entity_info["full"][0]["@value"]})
                    elif startswith:
                        if entity_info["abbrv"][0]["@value"].lower().startswith(q):
                            d.append({"id": entity_id, "name": entity_info["full"][0]["@value"], "count": entity_info["count"][0]["@value"]})
                    else:
                        if entity_info["abbrv"][0]["@value"].lower() == q:
                            d.append({"id": entity_id, "name": entity_info["full"][0]["@value"], "count": entity_info["count"][0]["@value"]})

            return_d.callback(d)

        store.get_latest(table_name).addCallback(got_latest)
        return return_d


    def try_to_find_entity(self, store, description, table_name):
        result_d = Deferred()

        parts = description.split()
        
        candidates = []
        
        tosearch = []
        for sublist in self.iter_sublists(parts):
            abbrv = ' '.join(sublist)
            tosearch.append( (store, abbrv, table_name) )

        def done_all_searches(candidates, q, table_name):    
            if table_name == 'places' and len(candidates) == 0:
                tosearch = []
                for sublist in self.iter_sublists(q.split()):
                    abbrv = ' '.join(sublist)
                    tosearch.append(abbrv)
                # search the gazetteer
                f = open(os.path.join(os.path.dirname(__file__), "uk_places.json"), "r")
                uk_places = json.load(f)
                f.close()
            
                for place in uk_places:
                    for search in tosearch:
                        if (place.lower() == search.lower()):
                            candidates.append({
                                'abbrv':    search,
                                'start':    q.find(search, 0),
                                'end':      q.find(search, 0) + len(search),
                                'full':     place,
                                'count':    1
                            })
            if len(candidates) == 0:
                result_d.callback(None)
            else:
                candidates = sorted(candidates, self.sort_candidates)
                result_d.callback(candidates[0])


        def do_search(matches, candidates, q, abbrv, in_table_name):
            if matches is not None:
                if len(matches) > 0:
                    for match in matches:
                        #if match not in candidates:
                        logging.debug("do_search: "+abbrv+" ("+q+")"+" ("+table_name+")")
                        candidates.append({
                            'abbrv':    abbrv,
                            'start':    q.find(abbrv, 0),
                            'end':      q.find(abbrv, 0) + len(abbrv),
                            'full':     match['name'],
                            'count':    match['count']
                        })


            if len(tosearch) > 0:
                store, abbrv, table_name = tosearch.pop(0)
                logging.debug("popped: "+repr(abbrv)+" ("+table_name+")")
                self.search_entity_for_term(store, abbrv, table_name).addCallback(lambda matches: do_search(matches, candidates, q, abbrv, in_table_name))
            else:
                done_all_searches(candidates, q, in_table_name)

        do_search(None, candidates, description, None, table_name)

        return result_d

        
        
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
