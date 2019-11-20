#!/usr/bin/python3

import re
import yaml
import psycopg2
import rocketbot
import json
from datetime import datetime

MY_USERNAME = 'jacky'
DBHOST = 'db.cat.pdx.edu'
DBNAME = 'network_db'
UNAME = 'jackson'

LIMIT = '5' #make sure the number is a character string
URL = 'https://intranet.cecs.pdx.edu/network/host/info/hostinfo.php?hostid='

#connect to db
conn=psycopg2.connect("host={} dbname={} user={}".format(DBHOST, DBNAME, UNAME))

#this will perform basic database operations
cur = conn.cursor()

# Jackson Bot Class
# interacts with users and databases to display network info
class JackBot(rocketbot.WebsocketRocketBot):
    # Override the handle_message method to do our own thing.
    def handle_chat_message(self, message):
        conn.rollback()
        input_json=message
        token = input_json['token']
        text = input_json['text']
        user_name = input_json['user_name']
        if user_name == 'irc':
            return
        if not re.search('^(?i)@jacky\s', text):
            self.logger.debug('Quiting')
            return
        #parse data
        recieved_string = input_json['text']
        recieved_string = recieved_string.lower()
        split_string = recieved_string.split( )
        answer = 0
        #call correct function
        if split_string[1] == 'hello':
            self.respond("hello")
            return
        elif split_string[1] == 'example':
            self.respond("jack g-d550, switchport Gi1/0/48, name tac, room eb-38                                                                                        5")
            return
        elif split_string[1] == 'help':
            self.help()
            return
        elif re.search('/\\d{1,2}/', split_string[1]):
            self.search_switchport(split_string[1], LIMIT)
            answer_quality = 1
        elif split_string[1] == 'jack':
            self.search_jack(split_string[2], LIMIT)
            answer_quality = 1
        elif split_string[1] == 'switchport':
            self.search_switchport(split_string[2], LIMIT)
            answer_quality = 1
        elif split_string[1] == 'name' or split_string[1] == 'host':
            self.search_name(split_string[2], LIMIT)
            answer_quality = 1
        elif split_string[1] == 'room':
            self.search_room(split_string[2])
            answer_quality = 1
        elif split_string[1] == 'room':
            self.search_room(split_string[2])
            answer_quality = 1
        elif split_string[1] == 'mac' or split_string[1] == 'macaddr' or split_s                                                                                        tring[1] == 'mac_addr':
            self.search_mac(split_string[2])
            answer_quality = 1
        if answer_quality != 1:
            #planning on replacing this with a string compare function that offe                                                                                        rs suggestions
            self.respond('{} request is not found, try typing your instruction a                                                                                        gain, or ask for help.'.format(user_name))
            return

    def help(self):
        self.respond('Enter what is needed (jack, switchport, or name) then what                                                                                         you are looking for (g-d550, gi1/0/48, or tac) type \"jack2 example\" for examp                                                                                        les')

    def search_jack(self, jack_name, LIMIT):
        command = '''
            SELECT jack.jackid,
                   jack.label,
                   jack.bldg,
                   jack.room,
                   jack.closet,
                   switchport.switch,
                   switchport.switchport
            FROM jack
                   left join wiring using (jackid)
                   left join switchport using (switch, switchport)
            WHERE lower(label)=lower(%s)
            '''
        cur.execute(command, (jack_name,))
        jack_info = cur.fetchall()
        #self.logger.debug('jack_info:')
        #self.logger.debug(jack_info)
        responce = ''
        for jack in jack_info:
            #self.logger.debug(jack_info.index(jack))
            #self.logger.debug(jack)
            temp_jackid, label, building, room, closet, switch, switchport = jac                                                                                        k
            jackid = str(temp_jackid)
            #self.logger.debug('Switch info: {}'.format(tmp_switch))

            command = '''
                        SELECT array_agg(hostname.name),
                            array_agg(hostname.hostid),
                            array_agg(hostmac.mac_addr)
                        FROM host2jack
                            join host using (hostid)
                            left join hostname using(hostid)
                            left join hostmac using(hostid)
                        WHERE jackid=(%s) group by hostid
                        '''

            cur.execute(command,(jackid,))
            machine_info = cur.fetchall()
            if not machine_info:
                responce = responce + 'Jack ' + label + ' is not plugged into a                                                                                         switch.\n'
            for machine in machine_info:
                machine_name, hostid, mac_addr = machine
                hostid = hostid[0]
                if not switch:
                    responce = responce + '[{machine_name}]({URL}{hostid}) shoul                                                                                        d be plugged into {label}. MAC= `{mac_addr}` location= {building} {room}. Howeve                                                                                        r, a switch is not identified as providing service to it.\n'.format(machine_name                                                                                        =machine_name,
                        URL = URL,
                        hostid = hostid,
                        label = label,
                        mac_addr = mac_addr,
                        building = building,
                        room = room)
                else:
                    responce = responce + '[{machine_name}]({URL}{hostid}) shoul                                                                                        d be plugged into {label}. MAC= `{mac_addr}` location= {building} {room}. At {sw                                                                                        itchport} using {switchjack}.\n'.format(machine_name=machine_name[0],
                        URL = URL,
                        hostid = hostid,
                        label = label,
                        mac_addr = mac_addr[0],
                        building = building,
                        room = room,
                        switchjack = switch,
                        switchport = switchport)

        if responce == '':
            responce = 'Nothing found';
        self.respond(responce)

    def search_switchport(self, switch_port, LIMIT):
        command =  '''
                    SELECT wiring.switch,
                        wiring.switchport,
                        wiring.jack,
                        jack.bldg,
                        jack.room,
                        host2jack.hostid
                    FROM wiring
                        left join jack using (jackid)
                        left join host2jack using (jackid)
                    WHERE lower(switchport)=lower(%s)
                   '''
        cur.execute(command, (switch_port,))
        switchports = cur.fetchall()
        if switchports == None:
            self.respond(switch_port + ' not found or not in use.')
            return
        #self.logger.debug('Switch info: ')
        #self.logger.debug(jack_info)
        responce = ''
        for switchport in switchports:
            switch, switchport, jack, bldg, room, hostid = switchport
            command =  '''
                        SELECT hostname.name,
                            hostmac.mac_addr
                        FROM hostname
                            left join hostmac using (hostid)
                        WHERE hostid=(%s)
                       '''
            cur.execute(command,(hostid,))
            machines = cur.fetchall()
            for machine in machines:
                if machine == None:
                    responce = responce + '{switchport} on {switch} is not conne                                                                                        cted to a machine\n'.format(switchport=switchport, switch=switch)
                hostname, mac_addr = machine
                responce = responce + '{switchport} on switch {switch} is connec                                                                                        ted to {jack} in room {bldg}-{room} servicing [{hostname}]({URL}{hostid}) with m                                                                                        ac of `{mac_addr}`\n'.format(switchport=switchport,
                        switch=switch,
                        jack=jack,
                        bldg=bldg,
                        room=room,
                        hostname=hostname,
                        URL=URL,
                        hostid=hostid,
                        mac_addr=mac_addr)
        self.respond(responce)

    def search_name(self, hostname, LIMIT):
        command = '''
                    SELECT hostname.name,
                        hostname.hostid,
                        hostmac.mac_addr,
                        jack.label,
                        jack.bldg,
                        jack.room,
                        jack.closet,
                        wiring.switch,
                        wiring.switchport
                    FROM hostname
                        left join host2jack using (hostid)
                        left join hostmac using (hostid)
                        left join jack using (jackid)
                        left join wiring using (jackid)
                    WHERE name ~* (%s)
                  '''
        cur.execute(command,(hostname,))
        hosts = cur.fetchall()
        if hosts == None:
            self.respond(hostname + " machine not found.")
        responce = ''
        for host in hosts:
            #self.respond(json.dumps(host))
            name, hostid, mac_addr, label, bldg, room, closet, switch, switchpor                                                                                        t = host
            if (switch == None) or (label == None):
                responce = responce + '[{name}]({URL}{hostid}) with MAC=`{mac_ad                                                                                        dr}` is not connected to a switch \n'.format(name=name,
                    URL=URL,
                    hostid=hostid,
                    mac_addr=mac_addr)

            else:
                responce = responce + '[{name}]({URL}{hostid}) with MAC=`{mac_ad                                                                                        dr}` is connected to jack {label} in {bldg}-{room} serviced by {switch} {switchp                                                                                        ort}\n'.format(name=name,
                    URL=URL,
                    hostid=hostid,
                    mac_addr=mac_addr,
                    label=label,
                    bldg=bldg,
                    room=room,
                    switch=switch,
                    switchport=switchport)

        if responce == '':
            responce = 'Nothing found';
        self.respond(responce)

    def search_room(self, place):
        place_split = place.split('-')
        bldg_search = place_split[0]
        room_search = place_split[1]
        command = '''
                     SELECT jack.closet,
                            jack.bldg,
                            jack.room,
                            jack.label,
                            wiring.switch,
                            wiring.switchport,
                            hostname.name,
                            hostname.hostid,
                            hostmac.mac_addr
                     FROM jack
                            left join wiring using (jackid)
                            left join host2jack using (jackid)
                            left join hostname using (hostid)
                            left join hostmac using (hostid)
                     WHERE lower(bldg)=lower(%s) and lower(room)=lower(%s)
                  '''
        cur.execute(command,(bldg_search,room_search))
        jacks = cur.fetchall()
        if jacks == None:
            self.respond("{bldg_search}-{room_search} was not found. Make sure t                                                                                        o use the format \"bldg-room\"".format(bldg_search=bldg_search, room_search=room                                                                                        _search))
        responce = ''
        for jack in jacks:
            #self.respond(json.dumps(jack))
            closet, bldg, room, label, switch, switchport, name, hostid, mac_add                                                                                        r = jack
            if switch == None and name == None:
                responce = responce + "{label} is not connected to a host or swi                                                                                        tch\n".format(label=label)
            elif switch == None:
                responce = responce + "{label} not connected to a switch, but is                                                                                         connected to [{name}]({URL}{hostid}) (mac `{mac_addr}`)\n".format(label=label,
                        name=name,
                        URL=URL,
                        hostid=hostid,
                        mac_addr=mac_addr)
            elif name == None:
                responce = responce + "{label} not connected to a host, but is w                                                                                        ired to {switch} {switchport}\n".format(label=label, switch=switch, switchport=s                                                                                        witchport)
            else:
                responce = responce + "{label} is connected to [{name}]({URL}{ho                                                                                        stid}) (mac `{mac_addr}`), and wired to {switch} {switchport}\n".format(label=la                                                                                        bel,
                        name=name,
                        URL=URL,
                        hostid=hostid,
                        mac_addr=mac_addr,
                        switch=switch,
                        switchport=switchport)
        if responce == '':
            responce = 'Nothing found';
        self.respond(responce)


    def search_mac(self, mac):
        #search by mac
        #add netmedia and dns.iphome
        command = '''
            SELECT hostmac.hostid,
                hostmac.mac_addr,
                hostname.name
            FROM hostmac
                left join hostname using (hostid)
            WHERE mac_addr=%s
            '''
        cur.execute(command,(mac,))
        hostmacs = cur.fetchall()
        if hostmacs == None:
                self.respond('{mac} was not found.'.format(mac=mac))
        responce = ''
        for hostmac in hostmacs:
            hostid, mac_addr, name = hostmac
            command = '''
                SELECT bridge.switch,
                        bridge.switchport,
                        jack.label,
                        host2jack.hostid,
                        hostname.name
                FROM bridge
                        left join wiring using (switch, switchport)
                        left join host2jack using (jackid)
                        left join jack using (jackid)
                        left join hostname using (hostid)
                        WHERE mac_addr=%s
                '''
            cur.execute(command,(mac,))
            bridgemacs = cur.fetchall()
            if bridgemacs == None:
                    self.respond('{mac} was not found in bridge database.'.forma                                                                                        t(mac=mac))
                    #exit()
            responce = ''
            for bridgemac in bridgemacs:
                switch, switchport, label, hostid2, name2 = bridgemac
                responce = responce + "`{mac_addr}` is associated with [{name}](                                                                                        {URL}{hostid}), connected to {label}, and wired to {switch} {switchport}\n".form                                                                                        at(mac_addr=mac_addr,
                        name=name,
                        URL=URL,
                        hostid=hostid,
                        label=label,
                        switch=switch,
                        switchport=switchport)
            if hostid2 == 1000:
                    responce += '`{mac}` is idenified as a laptop.'.format(mac=m                                                                                        ac)
        if responce == '':
            responce = 'Nothing found';
        self.respond(responce)


# Main Method
if __name__ == "__main__":
    # Pull config from a config file
    with open("rb.cfg", 'r') as cfg_file:
        cfg = yaml.load(cfg_file)
        domain = cfg["domain"]
        user = cfg["user"]
        password = cfg["password"]

    # Create the bot
    bot = JackBot(domain, user, password)

    # Make the bot run
    bot.start()
