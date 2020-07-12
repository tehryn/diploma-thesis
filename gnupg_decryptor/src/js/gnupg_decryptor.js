/* jshint esversion: 8 */
/* jshint node: true */
/* jshint browser: true */
/* jshint -W080 */

const encoder = new TextEncoder();

var browser = browser || chrome;
let MAX_MESSAGE_SIZE = 3 * 1024 * 1024 * 1024;
let elemId   = 0;
let blocks   = {};
let cache    = {};
let tabId    = undefined;
let types    = {};

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
                    //console.log( blocks.messageId );
                }
                else {
                    if ( typeof blocks[ message.messageId ] !== 'undefined' ) {
                        message.data = blocks[ message.messageId ] + message.data;
                    }
                    let elem = document.getElementById( message.messageId );

                    if ( types[ message.messageId ] == 'text' ) {
                        text = elem.innerHTML.trim();
                        hash = stringToHash( text );
                        if ( message.encoding == 'base64' ) {
                            cache[ hash ].data =  decodeURIComponent(escape(window.atob( message.data )));
                        }
                        else {
                            cache[ hash ].data = message.data;
                        }
                        cache[ hash ].status = 'decrypted';
                        cache[ hash ].elements.forEach(
                            function ( id, index ) {
                                elem = document.getElementById( id );
                                elem.innerHTML = cache[ hash ].data;
                            }
                        );
                    }
                    else if ( types[ message.messageId ] == 'file' ) {
                        let blob  = new Blob( [ base64ToArrayBuffer( message.data ) ], { type : message.mimeType } );
                        let url = URL.createObjectURL( blob );
                        cache[ elem.src ].url    = url;
                        cache[ elem.src ].status = 'decrypted';
                        cache[ elem.src ].elements.forEach(
                            function ( id, index ) {
                                elem = document.getElementById( id );
                                elem.src = url;
                                if ( elem.parentNode && ( elem.parentNode.tagName === 'VIDEO' || elem.parentNode.tagName === 'AUDIO' ) ) {
                                    elem.parentNode.load();
                                }
                            }
                        );
                    }
                }
            }
        }
        if ( message.type === "tabIdResponse" ) {
            tabId = message.tabId;
            console.log( 'New TabId: ' + tabId );
        }
    }
);

setTabId();
setTimeout( checkTabId, 100 );
function checkTabId() {
    if ( tabId !== undefined ) {
        main();
    }
    else {
        setTabId();
        setTimeout( checkTabId, 100 );
    }
}

function getId() {
    let newId = 'GnuPG_DecryptorElemId-' + elemId++;
    while ( document.getElementById( newId ) ) {
        newId = 'GnuPG_DecryptorElemId-' + elemId++;
    }

    return newId;
}

function setTabId() {
    sendMessage( { 'type' : 'tabIdRequest' } );
}

function main() {
    let mutObservConfig = { attributes : true, attributeFilter : [ 'src' ], childList : true, subtree : true, characterDataOldValue : true };
    let mutObserver = new MutationObserver(
        function( mutatuinList, observer ) {
            for ( let mutation of mutatuinList ) {
                console.log( cache );
                if ( mutation.type !== 'attributes1' ) {
                    let elements = getElements( mutation.target );
                    parseElements( elements );
                }
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
                if ( cache[ elem.data.src ] === undefined ) {
                    file = elem.data;
                    cache[ elem.data.src ] = { 'status' : 'creatingRequset', 'type' : 'file', 'url' : elem.data.src, 'elements' : [ id ] };
                    // We are working with encrypted files
                    let reader = new FileReader();

                    // reading the file
                    reader.onload = function( event ) {
                        let encrypted = arrayBufferToBase64( event.target.result );
                        let message   = { 'data' : encrypted, 'type' : 'decryptRequest', encoding : 'base64', messageId : id };
                        types[ id ] = 'file';
                        sendMessage( message );
                        cache[ elem.data.src ].status = 'decrypting';
                        console.log( 'Element ' + id + ' sent.' );
                    };

                    // getting the file as blob
                    getFile( elem.data.preParsedData ? elem.data.preParsedData : file.src, 'blob' ).then(
                        function( data ) {
                            reader.readAsArrayBuffer( data );
                        }
                    );
                }
                else {
                    if ( cache[ elem.data.src ].status === 'decrypted' ) {
                        elem.data.src = cache[ elem.data.src ].url;
                    }
                    else {
                        cache[ elem.data.src ].elements.push( id );
                    }
                }
            }
            else if ( elem.type == 'text' ) {
                data = elem.data.preParsedData ? elem.data.preParsedData : elem.data.innerHTML.trim();
                hash = stringToHash( data );
                if ( cache[ hash ] === undefined ) {
                    types[ id ] = 'text';
                    cache[ hash ] = { 'status' : 'decryptRquest', 'type' : 'text', 'data' : data, 'elements' : [ id ] };
                    sendMessage( { 'data' : data, 'type' : 'decryptRequest', encoding : 'ascii', messageId : id } );
                    console.log( 'Element ' + id + ' sent.' );
                }
                else {
                    if ( cache[ hash ].status === 'decrypted' ) {
                        elem.data.innerHTML = cache[ hash ].data;
                    }
                    else {
                        cache[ hash ].elements.push( id );
                    }
                }
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
        text = node.innerHTML.trim();
        if ( node.hasAttribute( 'src' ) && ( node.src.toLowerCase().endsWith( '.gpg' ) || node.src.toLowerCase().endsWith( '.asc' ) ) ) {
            arr.push( { 'data' : node, 'type' : 'file', 'preParsedData' : null } );
        }

        if ( node.children.length == 0 && text.startsWith( '-----BEGIN PGP MESSAGE-----' ) && text.match( armouredRegex ) ) {
            arr.push( { 'data' : node, 'type' : 'text', 'preParsedData' : text } );
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
    message.tabId = tabId;
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

function stringToHash( str ) {
    let hash = 0;

    for ( i = 0; i < str.length; i++ ) {
        hash = ( ( ( hash << 5 ) - hash ) + str.charCodeAt( i ) ) | 0;
    }

    return '' + hash;
}