from flask import Flask, request
import json
import os
import paramiko
import time
import requests
import digitalocean

app = Flask(__name__)


@app.route('/', methods=['POST'])
def main():
    print('==============VALID MESSAGE INCOMING==============')
    # Parse JSON
    data = request.data
    data = str(data)
    data = data[2:-1]
    data = json.loads(data)
    print('Data Loaded!')
    email = data['billing']['email']
    manager = digitalocean.Manager(token="TOKENHERE")


    try:
        print('Adding Key...')
        key = digitalocean.SSHKey(token='TOKENHERE',
                                  name=data['number'],
                                  public_key=data['customer_note'])
        key.create()
        print('Key Added!')
    except:
        print('Key already exists!')

    keys = manager.get_all_sshkeys()
    input (keys)
    keystore = [keys[len(keys) - 1], keys[1]]

    print('Creating Droplet...')
    droplet = digitalocean.Droplet(token='TOKENHERE',
                                   name=data['number'],
                                   region='fra1',
                                   image='plesk-18-04',
                                   size_slug='s-1vcpu-1gb',
                                   ssh_keys=keystore,
                                   backups=False)
    droplet.create()
    print('Droplet created. Awaiting setup... (This may take a while)')
    actions = droplet.get_actions()
    for action in actions:
        while action.status != 'completed':
            action.load()
            # Once it shows complete, droplet is up and running
    print('Droplet is now loaded')
    ldroplet = droplet.load()
    ip = ldroplet.ip_address
    print('IP address has been grabbed successfully!')

    print('Pinging IP address in 30 seconds to test connection')
    time.sleep(30)
    response = os.system('ping -c 1 ' + ip)
    if response == 0:
        print('Host Responded. Waiting 20secs for bootup to complete...')
        time.sleep(20)
        print('SSHing into droplet...')
        ssh = paramiko.client.SSHClient()
        keyfile = 'ssh/SSH'
        k = paramiko.RSAKey.from_private_key_file(keyfile,
                                                  password='SSHPASSHERE')
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, username='root', pkey=k)
        print('Grabbing Plesk login link')
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('sudo plesk login', get_pty=True)
        for line in iter(ssh_stdout.readline, ''):
            link = line
        print('Done proccessing droplet. Sending request to email...')
        ssh.close()
        data2send = {'link': link, 'email': email, 'ipv4': ip}
        res = requests.post('OUTHOOK', json=data2send)
        print('response from server:', res.text)
        dict_from_server = res.json()
        print(dict_from_server)
    else:
        print('Host was unresponsive')
    print('============END OF MESSAGE PROCESSING=============')
    return 'ok'


if __name__ == '__main__':
    app.run(host='calls.ionisedhosting.com', port=443, ssl_context=(
        '/etc/letsencrypt/live/calls.ionisedhosting.com/fullchain.pem',
        '/etc/letsencrypt/live/calls.ionisedhosting.com/privkey.pem'))
