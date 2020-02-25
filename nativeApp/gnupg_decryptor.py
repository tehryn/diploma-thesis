#!/usr/bin/python3 -u

# Note that running python with the `-u` flag is required on Windows,
# in order to ensure that stdin and stdout are opened in binary, rather
# than text, mode.

import json
import sys
import struct
import base64
import subprocess
import tkinter
import tkinter.simpledialog
import magic

from threading import Thread

def getpwd( message ):
    tkinter.Tk().withdraw()
    return tkinter.simpledialog.askstring(message, "Enter password:", show='*')

# Read a message from stdin and decode it.
def get_message():
    raw_length = sys.stdin.buffer.read(4)

    if not raw_length:
        sys.exit(0)
    message_length = struct.unpack('=I', raw_length)[0]
    message = sys.stdin.buffer.read(message_length).decode("utf-8")
    return json.loads(message)


# Encode a message for transmission, given its content.
def encode_message(message_content):
    encoded_content = json.dumps(message_content).encode("utf-8")
    encoded_length = struct.pack('=I', len(encoded_content))
    # use struct.pack("10s", bytes), to pack a string of the length of 10 characters
    return {'length': encoded_length, 'content': struct.pack(str(len(encoded_content))+"s",encoded_content)}


# Send an encoded message to stdout.
def send_message(encoded_message):
    sys.stdout.buffer.write(encoded_message['length'])
    sys.stdout.buffer.write(encoded_message['content'])
    sys.stdout.buffer.flush()

def debug( messageString ):
    send_message( encode_message( { 'message' : messageString, 'type' : 'debug' } ) )

#password = getpwd( 'Root password' ) + '\n'
#passwordKey = getpwd( 'Key password' )
password = base64.decodestring( 'dGVocnluY3NzMTI=\n'.encode() ).decode() + '\n';
passwordKey = '123456789'
mimeResolver = magic.Magic( mime=True )
largeRequests = dict()
MAX_MESSAGE_SIZE = 750 * 1024
while True:
    message = get_message()
    errorMessage = str()
    if ( message[ 'type' ] == 'decryptRequest' ):
        decodedData = None
        if ( message[ 'encoding' ] == 'base64' ):
            rawData = base64.b64decode( message[ 'data' ] )
        elif ( message[ 'encoding' ] == 'ascii' ):
            rawData = message[ 'data' ].encode()
        else:
            errorMessage = 'Invalid encoding: ' + message[ 'encoding' ]
            send_message( encode_message( { 'messageId' : message[ 'messageId' ], 'success' : 0, 'message' : errorMessage, 'type' : 'decryptResponse', 'data' : '' } ) )
            continue

        if ( message[ 'lastBlock' ] == 0 ):
            largeRequests[ message[ 'messageId' ] ] = largeRequests[ message[ 'messageId' ] ] + rawData if ( message[ 'messageId' ] in largeRequests ) else rawData
            continue
        elif ( message[ 'messageId' ] in largeRequests ):
            rawData = largeRequests[ message[ 'messageId' ] ] + rawData
            debug( 'Message is commplete' )
            del( largeRequests[ message[ 'messageId' ] ] )

        process = subprocess.Popen( [ 'sudo', '-Sk' ,'gpg', '--passphrase', passwordKey, '--decrypt' ] ,stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE )
        decrypted, err = process.communicate( password.encode() + rawData )
        retcode = process.returncode
        debug( "Error:" + str( err ) )

        if ( retcode != 0 ):
            errorMessage = 'Unable to decrypt data: ' + err.decode()
            send_message( encode_message( { 'messageId' : message[ 'messageId' ], 'success' : 0, 'message' : errorMessage, 'type' : 'decryptResponse', 'data' : '' } ) )
            continue

        mimeType  = mimeResolver.from_buffer( decrypted )
        decrypted = base64.b64encode( decrypted )
        blocks    = [ decrypted[ i : i + MAX_MESSAGE_SIZE ] for i in range( 0, len( decrypted ), MAX_MESSAGE_SIZE ) ]
        lastBlock = blocks.pop()
        response  = { 'messageId' : message[ 'messageId' ], 'success' : 1, 'message' : '', 'type' : 'decryptResponse', 'data' : '', 'encoding' : 'base64', 'mimeType' : mimeType, 'lastBlock' : 0 }

        for block in blocks:
            response[ 'data' ] = block.decode()
            send_message( encode_message( response ) )
        response[ 'data' ]      = lastBlock.decode()
        response[ 'lastBlock' ] = 1
        send_message( encode_message( response ) )
            