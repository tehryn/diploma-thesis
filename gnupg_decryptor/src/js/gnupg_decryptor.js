/* jshint esversion: 8 */
/* jshint node: true */
/* jshint browser: true */
/* jshint -W080 */

const encoder = new TextEncoder();

var browser = browser || chrome;
let MAX_MESSAGE_SIZE = 3 * 1024 * 1024 * 1024;
let elemId  = 0;
let blocks  = {};


document.body.style.border = "5px solid blue";
browser.runtime.onMessage.addListener(
    function( message, sender, sendResponse ) {
        //console.log( message );
        if ( message.type === "decryptResponse" ) {
            if ( message.success === 1 ) {
                if ( message.lastBlock === 0 ) {
                    if ( typeof blocks[ message.messageId ] === 'undefined' ) {
                        blocks[ message.messageId ] = message.data;
                    }
                    else {
                        blocks[ message.messageId ] += message.data;
                    }
                    console.log( blocks.messageId );
                }
                else {
                    if ( typeof blocks[ message.messageId ] !== 'undefined' ) {
                        message.data = blocks[ message.messageId ] + message.data;
                    }
                    if ( message.mimeType.startsWith( 'text' ) ) {
                        let elem = document.getElementById( message.messageId );
                        if ( message.encoding == 'base64' ) {
                            elem.innerHTML = window.atob( message.data );
                        }
                        else {
                            elem.innerHTML = message.data;
                        }
                    }
                    else {
                        let blob  = new Blob( [base64ToArrayBuffer( message.data )], { type : message.mimeType } );
                        let url = URL.createObjectURL( blob );
                        let elem = document.getElementById( message.messageId );
                        elem.src = url;
                        if ( elem.parentNode && ( elem.parentNode.tagName === 'VIDEO' || elem.parentNode.tagName === 'AUDIO' ) ) {
                            elem.parentNode.load();
                        }
                    }
                }
            }
        }
    }
);


main();

function getId() {
    let newId = 'GnuPG_DecryptorElemId-' + elemId++;
    while ( document.getElementById( newId ) ) {
        newId = 'GnuPG_DecryptorElemId-' + elemId++;
    }

    return newId;
}

function main() {
    let mutObservConfig = { attributes : true, childList : true, subtree : true };
    let mutObserver = new MutationObserver(
        function( mutatuinList, observer ) {
            for ( let mutation of mutatuinList ) {
                console.log( mutation );
                let elements = getElements( mutation.target );
                parseElements( elements );
            }
        }
    );
    mutObserver.observe( document.documentElement, mutObservConfig );
    let elements = getElements( document.documentElement );
    parseElements( elements );
}

function mergeArrayBuffers( arr1, arr2, arr3 ) {
    let result = new Uint8Array( arr1.byteLength + arr2.byteLength + arr3.byteLength );
    result.set( new Uint8Array( arr1 ), 0 );
    result.set( new Uint8Array( arr2 ), arr1.byteLength );
    result.set( new Uint8Array( arr3 ), arr1.byteLength + arr2.byteLength );
    return result.buffer;
}

function parseElements( elements ) {
    elements.forEach(
        function( elem, index ) {
            let id = elem.data.id;
            if ( !elem.data.id ) {
                elem.data.id = id = getId();
            }
            console.log( 'Parsing elemnt: ' + id );
            if ( elem.type === 'file' ) {
                img = elem.data;
                // We are working with encrypted files
                let reader = new FileReader();

                // reading the file
                reader.onload = function( event ) {
                    console.log( 'Element loaded, preparing to send: ' + id );
                    let encrypted = arrayBufferToBase64( event.target.result );
                    let message   = { 'data' : encrypted, 'type' : 'decryptRequest', encoding : 'base64', messageId : id };
                    sendMessage( message );
                };

                // getting the file as blob
                getFile( img.src, 'blob' ).then(
                    function( data ) {
                        reader.readAsArrayBuffer( data );
                    }
                );
            }
            else if ( elem.type == 'text' ) {
                let message   = { 'data' : elem.data.innerHTML.trim(), 'type' : 'decryptRequest', encoding : 'ascii', messageId : id };
                sendMessage( message );
            }
        }
    );
}

function getElements( root ) {
    let arr = [];
    let iterator = document.createNodeIterator( root, NodeFilter.SHOW_ELEMENT );
    let node   = root;
    //let armouredRegex = new RegExp( '^-----BEGIN PGP MESSAGE(, PART [1-9][0-9]*(\/[1-9][0-9]*)?)?-----[aA-zZ|0-9|\\/+=\r\n]+-----END PGP MESSAGE-----$' );
    let armouredRegex = new RegExp( '^-----BEGIN PGP MESSAGE-----[aA-zZ|0-9|\\/+=\\r\\n]+-----END PGP MESSAGE-----$' );

    while ( node ) {
        if ( node.hasAttribute( 'src' ) && ( node.src.toLowerCase().endsWith( '.gpg' ) || node.src.toLowerCase().endsWith( '.asc' ) ) ) {
            arr.push( { 'data' : node, 'type' : 'file' } );
        }

        if ( node.children.length == 0 && node.innerHTML.trim().match( armouredRegex ) ) {
            arr.push( { 'data' : node, 'type' : 'text' } );
        }

        node = iterator.nextNode();
    }
    console.log( arr );
    return arr;
}

function getFile( url, type ) {
    return new Promise(
        function(resolve, reject) {
            try {
                let xhr = new XMLHttpRequest();
                xhr.open( 'GET', url );
                xhr.responseType = type;
                xhr.onerror = function() {
                    reject( 'Network error.' );
                };
                xhr.onload = function() {
                    if ( xhr.status === 200 ) {
                        resolve(xhr.response);
                    }
                    else {
                        reject( 'Loading error:' + xhr.statusText );
                    }
                };
                xhr.send();
            }
            catch( err ) {
                reject( err.message );
            }
        }
    );
}

function arrayBufferToBase64( buffer ) {
    var binary = '';
    var bytes = new Uint8Array( buffer );
    var len = bytes.byteLength;
    for (var i = 0; i < len; i++) {
        binary += String.fromCharCode( bytes[ i ] );
    }
    return window.btoa( binary );
}

function base64ToArrayBuffer(base64) {
    let binary_string = window.atob(base64);
    let len = binary_string.length;
    let bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) {
        bytes[i] = binary_string.charCodeAt(i);
    }
    return bytes.buffer;
}

function readAllChunks(readableStream) {
  const reader = readableStream.getReader();
  const chunks = [];

  function pump() {
    return reader.read().then( ( { value, done } ) => {
        if ( done ) {
            return chunks;
        }
        chunks.push( value );
        return pump();
    });
  }

  return pump();
}

function sendMessage( message ) {
    //console.log( 'Sending:' + message.messageId );
    if ( message.type === 'decryptRequest' ) {
        let dataSize   = message.data.length;
        //console.log( 'Total size of data (curr/max): ' + dataSize + '/' + MAX_MESSAGE_SIZE );
        if ( dataSize > MAX_MESSAGE_SIZE ) {
        //    console.log( 'Spliting string...' );
            let dataBlocks = splitString( message.data );
        //    console.log( 'Data blocks count: ' + dataBlocks.length );
            dataBlocks.forEach(
                function( data, index ) {
                    //console.log( 'Part of data (size/length): ' + [ data.length, ( new TextEncoder().encode( data ) ).length ] );
                    message.data = data;
                    message.lastBlock = ( index + 1 == dataBlocks.length ) ? 1 : 0;
                    browser.runtime.sendMessage( message );
                }
            );
        }
        else {
            message.lastBlock = 1;
            browser.runtime.sendMessage( message );
        }
    }
    else {
        message.lastBlock = 1;
        browser.runtime.sendMessage( message );
    }
}

function splitString( string ) {
    let result = [];
    let steps  = Math.ceil( string.length / MAX_MESSAGE_SIZE );
    for( let i = 0; i < steps; i++ ) {
        result.push( string.substring( i * MAX_MESSAGE_SIZE, ( i + 1 ) * MAX_MESSAGE_SIZE ) );
    }
    return result;
}