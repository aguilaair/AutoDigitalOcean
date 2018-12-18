from flask import Flask, request
import json
import os
import paramiko
import time
import requests
import digitalocean
import hmac
import hashlib
import base64

app = Flask(__name__)


@app.route('/', methods=['POST'])
def main():
    print('==============VALID MESSAGE INCOMING==============')
    secret = '<SECRET HERE>'
    body = request.data
    body = str(body)
    body = body[2:-1]
    dig = hmac.new(secret.encode(), msg=body.encode(), digestmod=hashlib.sha256).digest()
    if request.headers.get('X-WC-Webhook-Signature') != base64.b64encode(dig).decode():
        return 'invalid signature'
    else:
        print('Webhook auth correct!')
    # Parse JSON
    data = request.data
    data = str(data)
    data = data[2:-1]
    try:
        data = json.loads(data)
    except:
        return 'Load Error'
    print('Data Loaded!')
    email = data['billing']['email']
    manager = digitalocean.Manager(token="<TOKEN HERE>")

    keys = manager.get_all_sshkeys()
    keystore = [keys[1]]

    print('Creating Droplet...')
    droplet = digitalocean.Droplet(token='<TOKEN HERE>',
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
                                                  password='<PASS HERE>')
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, username='root', pkey=k)
        print('Grabbing Plesk login link')
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('sudo plesk login', get_pty=True)
        for line in iter(ssh_stdout.readline, ''):
            link = line
        print('Done proccessing droplet. Sending request to email...')
        ssh.close()
        data2send = {'link': link, 'email': email, 'ipv4': ip}
        res = requests.post('<WEEBHOOK OUT HERE>', json=data2send)
        print('response from server:', res.text)
        dict_from_server = res.json()
        print(dict_from_server)
    else:
        print('Host was unresponsive')
    print('============END OF MESSAGE PROCESSING=============')
    return 'ok'


if __name__ == '__main__':
    app.run(host='<URL HERE>', port=443, ssl_context=(
        '<LENC HERE>/fullchain.pem',
        '<LENC HERE>/privkey.pem'))
