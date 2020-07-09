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
        args.append( '--list-secret-keys' )

        if ( settings[ 'home' ][ 'use' ] ):
            args.append( '--homedir' )
            args.append( settings[ 'home' ][ 'homedir' ] )

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

        self.updateKeys()

    def getKeyId( self, data ):
        args = [ 'gpg', '-d', '--list-only' ]
        process = subprocess.Popen( args ,stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE )
        _, stderr = process.communicate( data )
        retcode = process.returncode
        keys  = []
        if ( retcode == 0 ):
            stderr = stderr.decode().splitlines()
            keys = [ line.strip()[1:-1] for line in stderr if not line.startswith( 'gpg' )  ]
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
            errorMessage = str()
            if ( message[ 'type' ] == 'decryptRequest' ):
                if ( message[ 'encoding' ] == 'base64' ):
                    rawData = base64.b64decode( message[ 'data' ] )
                elif ( message[ 'encoding' ] == 'ascii' ):
                    rawData = message[ 'data' ].encode()
                else:
                    errorMessage = 'Invalid encoding: ' + message[ 'encoding' ]
                    self.send_message( self.encode_message( { 'messageId' : message[ 'messageId' ], 'success' : 0, 'message' : errorMessage, 'type' : 'decryptResponse', 'data' : '' } ) )
                    continue

                if ( message[ 'lastBlock' ] == 0 ):
                    largeRequests[ message[ 'messageId' ] ] = largeRequests[ message[ 'messageId' ] ] + rawData if ( message[ 'messageId' ] in largeRequests ) else rawData
                    continue
                elif ( message[ 'messageId' ] in largeRequests ):
                    rawData = largeRequests[ message[ 'messageId' ] ] + rawData
                    self.debug( 'Message is commplete' )
                    del( largeRequests[ message[ 'messageId' ] ] )

                keys = self.getKeyId( rawData )
                keys = [ key for key in keys if key in self._passwords ]

                if ( keys ):
                    process = subprocess.Popen( [ 'sudo', '-Sk' ,'gpg', '--passphrase', self._passwords[ keys[0] ], '--decrypt' ] ,stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE )
                    password = '' if self._sudo is None else self._sudo + '\n'
                    decrypted, err = process.communicate( password.encode() + rawData )
                    retcode = process.returncode
                    self.debug( "Error:" + str( err ) )

                    if ( retcode != 0 ):
                        errorMessage = 'Unable to decrypt data: ' + err.decode()
                        self.send_message( self.encode_message( { 'messageId' : message[ 'messageId' ], 'success' : 0, 'message' : errorMessage, 'type' : 'decryptResponse', 'data' : '' } ) )
                        continue

                    mimeType  = mimeResolver.from_buffer( decrypted )
                    decrypted = base64.b64encode( decrypted )
                    blocks    = [ decrypted[ i : i + MAX_MESSAGE_SIZE ] for i in range( 0, len( decrypted ), MAX_MESSAGE_SIZE ) ]
                    lastBlock = blocks.pop()
                    response  = { 'messageId' : message[ 'messageId' ], 'success' : 1, 'message' : '', 'type' : 'decryptResponse', 'data' : '', 'encoding' : 'base64', 'mimeType' : mimeType, 'lastBlock' : 0 }

                    for block in blocks:
                        response[ 'data' ] = block.decode()
                        self.send_message( self.encode_message( response ) )
                    response[ 'data' ]      = lastBlock.decode()
                    response[ 'lastBlock' ] = 1
                    self.send_message( self.encode_message( response ) )
                else:
                    errorMessage = 'Unable to decrypt data: Required key is not present'
                    self.send_message( self.encode_message( { 'messageId' : message[ 'messageId' ], 'success' : 0, 'message' : errorMessage, 'type' : 'decryptResponse', 'data' : '' } ) )
            elif ( message[ 'type' ] == 'displayWindow' ):
                self.show()
            elif ( message[ 'type' ] == 'getKeysResponse' ):
                self._passwords = message[ 'keys' ]

app = GnuPG_Decryptor()
app.main()