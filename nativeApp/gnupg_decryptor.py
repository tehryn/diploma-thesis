#!/usr/bin/python3 -u

# Note that running python with the `-u` flag is required on Windows,
# in order to ensure that stdin and stdout are opened in binary, rather
# than text, mode.

import json
import sys
import struct
import base64
import subprocess
import magic
from PyQt5.QtWidgets import QApplication
from GUI import GnuPG_Decryptor_GUI

class GnuPG_Decryptor:
    def __init__( self ):
        self._passwords = dict()
        self._gui       = None
        self._QApp      = None
        self._sudo      = None
        self._homedir   = None

    def show( self ):
        if( self._gui is None ):
            self._QApp = QApplication( sys.argv )
            initKeys = []
            for id, password in self._passwords:
                initKeys.append( { 'id' : id, 'password' : password } )
            self._gui  = GnuPG_Decryptor_GUI( self, initKeys )
        self._gui.show()
        return self._QApp.exec_()

    def keyList( self, settings ):
        stdin = ''
        args  = []

        if ( settings[ 'sudo' ][ 'use' ] ):
            args.append( 'sudo' )
            args.append( '-Sk' )
            stdin += settings[ 'sudo' ][ 'password' ] + '\n'

        args.append( 'gpg' )

        if ( settings[ 'home' ][ 'use' ] ):
            args.append( '--homedir' )
            args.append( settings[ 'home' ][ 'homedir' ] )

        args.append( '--list-secret-keys' )

        self.debug( 'Settigs: ' + str(settings) )
        self.debug( 'Arguments: ' + str( args ) )
        process = subprocess.Popen( args ,stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE )
        stdout, _ = process.communicate( stdin.encode() )
        retcode = process.returncode
        ids    = []
        if ( retcode == 0 ):
            stdout = stdout.decode().splitlines()
            uids   = [ line[3:].strip() for line in stdout if line.startswith( 'uid' ) ]
            for line in uids:
                idx = line.find( ' ' )
                ids.append( { 'id' : line[ idx + 1 : ], 'password' : '' } )
        return { 'returnCode' : retcode, 'keys' : ids }

    def setPasswords( self, config ):
        self._passwords = dict()
        for key in config[ 'keys' ]:
            self._passwords[ key[ 'id' ] ] = key[ 'password' ]

        if ( config[ 'sudo' ][ 'use' ] ):
            self._sudo = config[ 'sudo' ][ 'password' ]
        else:
            self._sudo = None

        if ( config[ 'home' ][ 'use' ] ):
            self._homedir = config[ 'home' ][ 'homedir' ]
        else:
            self._homedir = None

        self.debug( 'Config: ' + str(config) )
        self.debug( 'New passwords: ' + str( self._passwords ) )
        self.updateKeys()

    def getKeyUidFromId( self, keyId ):
        args      = [ 'gpg' ]
        if ( not self._homedir is None ):
            args.append( '--homedir' )
            args.append( self._homedir )

        args.append( '--list-public-keys' )
        args.append( '--fingerprint' )
        args.append( keyId )
        self.debug( str(args) )
        process   = subprocess.Popen( args ,stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE )
        stdout, _ = process.communicate()
        retcode   = process.returncode
        uid       = None
        self.debug( stdout.decode() )
        if ( retcode == 0 ):
            stdout = stdout.decode().splitlines()
            uids   = [ line[3:].strip() for line in stdout if line.startswith( 'uid' ) ]
            if ( uids ):
                uid = uids[0]
                idx = uid.find( ' ' )
                uid = uid[ idx + 1 : ]
        return uid

    def getKeyUidFromData( self, data ):
        args = [ 'gpg', '-d', '--list-only' ]
        process = subprocess.Popen( args ,stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE )
        _, stderr = process.communicate( data )
        retcode = process.returncode
        keys  = []
        self.debug( 'KEY IDs: ' + stderr.decode() )
        if ( retcode == 0 ):
            stderr   = stderr.decode().splitlines()
            filtered = [ line for line in stderr if line.startswith( 'gpg: encrypted' )  ]
            for line in filtered:
                self.debug( line )
                idx1 = line.find( ', ID' ) + 5
                idx2 = line.find( ',', idx1 )
                if ( idx2 == -1 ):
                    idx2 = len( line )
                self.debug( line )
                self.debug( idx1 )
                self.debug( idx2 )
                uid = self.getKeyUidFromId( line[ idx1 : idx2 ] )
                if ( not uid is None ):
                    keys.append( uid )
        return keys

    # Read a message from stdin and decode it.
    def get_message( self ):
        raw_length = sys.stdin.buffer.read(4)

        if not raw_length:
            sys.exit(0)
        message_length = struct.unpack('=I', raw_length)[0]
        message = sys.stdin.buffer.read(message_length).decode("utf-8")
        return json.loads(message)


    # Encode a message for transmission, given its content.
    def encode_message( self, message_content ):
        encoded_content = json.dumps(message_content).encode("utf-8")
        encoded_length = struct.pack('=I', len(encoded_content))
        # use struct.pack("10s", bytes), to pack a string of the length of 10 characters
        return {'length': encoded_length, 'content': struct.pack(str(len(encoded_content))+"s",encoded_content)}


    # Send an encoded message to stdout.
    def send_message( self, encoded_message ):
        sys.stdout.buffer.write( encoded_message['length'] )
        sys.stdout.buffer.write( encoded_message['content'] )
        sys.stdout.buffer.flush()

    def debug( self, messageString ):
        self.send_message( self.encode_message( { 'message' : messageString, 'type' : 'debug' } ) )

    def loadKeys( self ):
        self.send_message( self.encode_message( { 'type' : 'getKeysRequest' } ) )

    def updateKeys( self ):
        self.send_message( self.encode_message( { 'type' : 'updateKeysRequest', 'keys' : self._passwords } ) )

    def main( self ):
        mimeResolver = magic.Magic( mime=True )
        largeRequests = dict()
        MAX_MESSAGE_SIZE = 750 * 1024
        self.loadKeys()
        while True:
            message = self.get_message()
            self.debug( 'Got message' )
            errorMessage = str()
            if ( message[ 'type' ] == 'decryptRequest' and 'tabId' in message ):
                tabId = message[ 'tabId' ]
                if ( message[ 'encoding' ] == 'base64' ):
                    rawData = base64.b64decode( message[ 'data' ] )
                elif ( message[ 'encoding' ] == 'ascii' ):
                    rawData = message[ 'data' ].encode()
                else:
                    errorMessage = 'Invalid encoding: ' + message[ 'encoding' ]
                    self.send_message( self.encode_message( { 'messageId' : message[ 'messageId' ], 'success' : 0, 'message' : errorMessage, 'type' : 'decryptResponse', 'data' : '', 'tabId' : tabId } ) )
                    continue

                if ( message[ 'lastBlock' ] == 0 ):
                    largeRequests[ message[ 'messageId' ] ] = largeRequests[ message[ 'messageId' ] ] + rawData if ( message[ 'messageId' ] in largeRequests ) else rawData
                    continue
                elif ( message[ 'messageId' ] in largeRequests ):
                    rawData = largeRequests[ message[ 'messageId' ] ] + rawData
                    self.debug( 'Message is commplete' )
                    del( largeRequests[ message[ 'messageId' ] ] )

                self.debug( 'Passwords: ' + str(self._passwords) )
                keys = self.getKeyUidFromData( rawData )
                self.debug( 'Before filter: ' + str(keys) )
                keys = [ key for key in keys if key in self._passwords ]
                self.debug( 'After filter: ' + str(keys) )

                if ( keys ):
                    args     = []
                    sudoPass = ''
                    keyPass  = self._passwords[ keys[0] ]

                    if ( not self._sudo is None ):
                        args.append( 'sudo' )
                        args.append( '-Sk' )
                        sudoPass = self._sudo + '\n'

                    args.append( 'gpg' )
                    if ( not self._homedir is None ):
                        args.append( '--homedir' )
                        args.append( self._homedir )

                    args.append( '--quiet' )

                    if ( keyPass ):
                        args.append( '--no-tty' )
                        args.append( '--passphrase' )
                        args.append( keyPass )

                    args.append( '--decrypt' )

                    self.debug( str( args ) )
                    process = subprocess.Popen( args ,stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE )
                    decrypted, err = process.communicate( sudoPass.encode() + rawData )
                    retcode = process.returncode
                    self.debug( 'STDERR: ' + str( err ) )

                    if ( retcode != 0 ):
                        errorMessage = 'Unable to decrypt data: ' + err.decode()
                        self.send_message( self.encode_message( { 'messageId' : message[ 'messageId' ], 'success' : 0, 'message' : errorMessage, 'type' : 'decryptResponse', 'data' : '', 'tabId' : tabId } ) )
                        continue

                    mimeType  = mimeResolver.from_buffer( decrypted )
                    decrypted = base64.b64encode( decrypted )
                    blocks    = [ decrypted[ i : i + MAX_MESSAGE_SIZE ] for i in range( 0, len( decrypted ), MAX_MESSAGE_SIZE ) ]
                    lastBlock = blocks.pop()
                    response  = { 'messageId' : message[ 'messageId' ], 'success' : 1, 'message' : '', 'type' : 'decryptResponse', 'data' : '', 'encoding' : 'base64', 'mimeType' : mimeType, 'lastBlock' : 0, 'tabId' : tabId }

                    for block in blocks:
                        response[ 'data' ] = block.decode()
                        self.send_message( self.encode_message( response ) )
                    response[ 'data' ]      = lastBlock.decode()
                    response[ 'lastBlock' ] = 1
                    self.send_message( self.encode_message( response ) )
                else:
                    errorMessage = 'Unable to decrypt data: Required key is not present'
                    self.send_message( self.encode_message( { 'messageId' : message[ 'messageId' ], 'success' : 0, 'message' : errorMessage, 'type' : 'decryptResponse', 'data' : '', 'tabId' : tabId } ) )
            elif ( message[ 'type' ] == 'displayWindow' ):
                self.show()
            elif ( message[ 'type' ] == 'getKeysResponse' ):
                self._passwords = message[ 'keys' ]

app = GnuPG_Decryptor()
app.main()