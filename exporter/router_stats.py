#!/usr/bin/env python

from base import OSBase

from prometheus_client import CollectorRegistry, generate_latest, Gauge
import collections
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s:%(levelname)s:%(message)s")
logger = logging.getLogger(__name__)

class RouterStats(OSBase):
    """ Class to report the statistics on Neutron IPs.

        status per service broken down by state
    """
    def __init__(
            self,
            oscache,
            osclient,
            max_number_router):
        super(RouterStats, self).__init__(oscache, osclient)
        self.max_number_router = max_number_router

    def build_cache_data(self):

        cache_stats = []

        r = self.osclient.get('neutron', 'v2.0/routers')
        if not r:
            logger.warning("Could not get routers list")
        else:
            routers = r.json().get('routers', [])

            router_state = {}
            router_state.update({'multiple_active': 0, 'one_active': 0, 'more_than_max': 0, 'same_as_max': 0, 'less_than_max': 0})

            count_status = collections.Counter(d['status'] for d in routers)
            total_routers = sum(count_status[item] for item in count_status)
            router_up = collections.Counter(d['admin_state_up'] for d in routers)

            for router in routers:
                t = self.osclient.get('neutron', 'v2.0/routers/'+router['id']+'/l3-agents')
                if not t:
                    logger.warning("Could not get agent list for router "+router['id'])
                else:
                    agents_l3 = t.json().get('agents', [])
                    count_ha_state = collections.Counter(d['ha_state'] for d in agents_l3)
                    if count_ha_state['active'] > 1:
                        router_state['multiple_active'] += 1
                    else:
                        router_state['one_active'] += 1
                    if len(agents_l3) > self.max_number_router:
                        router_state['more_than_max'] += 1
                    elif len(agents_l3) == self.max_number_router:
                        router_state['same_as_max'] += 1
                    else:
                        router_state['less_than_max'] += 1

            for k, v in router_state.iteritems():
                prct = (100 * v) / total_routers
                cache_stats.append({
                    'stat_name': 'router_with_'+k+'_total',
                    'stat_value': v
                })
                cache_stats.append({
                    'stat_name': 'router_with_'+k+'_percent',
                    'stat_value': prct
                })

            for k, v in count_status.iteritems():
                prct = (100 * v) / total_routers
                cache_stats.append({
                    'stat_name': 'router_'+k.lower()+'_total',
                    'stat_value': v
                })
                cache_stats.append({
                    'stat_name': 'router_'+k.lower()+'_percent',
                    'stat_value': prct
                })

            for k, v in router_up.iteritems():
                prct = (100 * v) / total_routers
                cache_stats.append({
                    'stat_name': 'router_admin_up_total' if k else 'router_admin_down_total',
                    'stat_value': v
                })
                cache_stats.append({
                    'stat_name': 'router_admin_up_percent' if k else 'router_admin_down_percent',
                    'stat_value': prct
                })
            
            cache_stats.append({
                'stat_name': 'router_total',
                'stat_value': total_routers
            })


        return cache_stats
    
    def get_cache_key(self):
        return "router_stats"

    def get_stats(self):
        registry = CollectorRegistry()
        labels = ['region']
        router_stats_cache = self.get_cache_data()
        for router_stat in router_stats_cache:
            stat_gauge = Gauge(
                self.gauge_name_sanitize(
                    router_stat['stat_name']),
                'OpenStack Router Statistic',
                labels,
                registry=registry)
            label_values = [self.osclient.region]
            stat_gauge.labels(*label_values).set(router_stat['stat_value'])
        return generate_latest(registry)
