#!/usr/bin/env python

from base import OSBase

from prometheus_client import CollectorRegistry, generate_latest, Gauge
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s:%(levelname)s:%(message)s")
logger = logging.getLogger(__name__)

class NeutronIpStats(OSBase):
    """ Class to report the statistics on Neutron IPs.

        status per service broken down by state
    """
    
    def __init__(
            self,
            oscache,
            osclient):
        super(NeutronIpStats, self).__init__(oscache, osclient)

    def build_cache_data(self):
        cache_stats = []
        r = self.osclient.get('neutron', 'v2.0/network-ip-availabilities')
        if not r:
            logger.warning("Could not get ip availabilities")
        else:
            network_ip_availabilities_list = r.json().get('network_ip_availabilities', [])
            for network in network_ip_availabilities_list:
                for subnet in network['subnet_ip_availability']:
                    cache_stats.append({
                        'stat_name': 'total_ips',
                        'stat_value': subnet['total_ips'],
                        'subnet': subnet['subnet_name'],
                        'subnet_id': subnet['subnet_id'],
                        'network': network['network_name'],
                        'network_id': network['network_id']
                    })
                    cache_stats.append({
                        'stat_name': 'used_ips',
                        'stat_value': subnet['used_ips'],
                        'subnet': subnet['subnet_name'],
                        'subnet_id': subnet['subnet_id'],
                        'network': network['network_name'],
                        'network_id': network['network_id']                     
                    })
        return cache_stats
    
    def get_cache_key(self):
        return "ip_stats"

    def get_stats(self):
        registry = CollectorRegistry()
        labels = ['region', 'network', 'network_id', 'subnet', 'subnet_id']
        ip_stats_cache = self.get_cache_data()
        for ip_stat in ip_stats_cache:
            stat_gauge = Gauge(
                self.gauge_name_sanitize(
                    ip_stat['stat_name']),
                'OpenStack IP Statistic',
                labels,
                registry=registry)
            label_values = [self.osclient.region,
                            ip_stat.get('network', ''),
                            ip_stat.get('network_id', ''),
                            ip_stat.get('subnet', ''),
                            ip_stat.get('subnet_id', '')]
            stat_gauge.labels(*label_values).set(ip_stat['stat_value'])
        return generate_latest(registry)
