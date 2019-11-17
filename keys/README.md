#GPG

## GPG passwords
Password for test keys: 123456789

## GPG problems

### IOCTL 
gpg: dešifrování veřejným klíčem selhalo: Pro toto zařízení nevhodné ioctl
gpg: dešifrování selhalo: Žádný tajný klíč

How to solve:

Modify ~/.gnupg/gpg.conf:
use-agent 
pinentry-mode loopback

Modify: ~/.gnupg/gpg-agent.conf
allow-loopback-pinentry

Then:
echo RELOADAGENT | gpg-connect-agent