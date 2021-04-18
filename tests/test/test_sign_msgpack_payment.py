import pytest
import logging
import struct
import base64

import msgpack
import nacl.signing

import algosdk
from . import txn_utils
from . import ui_interaction

from . import speculos

@pytest.fixture
def payment_txn():
    return  algosdk.transaction.PaymentTxn(
        sender="YK54TGVZ37C7P76GKLXTY2LAH2522VD3U2434HRKE7NMXA65VHJVLFVOE4",
        receiver="RNZZNMS5L35EF6IQHH24ISSYQIKTUTWKGCB4Q5PBYYSTVB5EYDQRVYWMLE",
        fee=30000,
        flat_fee=True,
        amt=1000000,
        first=5667360,
        last=5668360,
        note="Hello World".encode(),
        gen="testnet-v1.0",
        close_remainder_to="NWBZBIROXZQEETCDKX6IZVVBV4EY637KCIX56LE5EHIQERCTSDYGXWG6PU",
        gh="SGO1GKSzyE7IEPItTxCByw9x8FmnrCDexi9/cOUJOiI=",
    )


def get_expected_messages(txn):
    messages =  [['review', 'transaction'],
             ['txn type', 'payment'],
             ['sender', txn.sender.lower()],
             ['fee (alg)', str(txn.fee /1000000)],
             ['genesis id', txn.genesis_id.lower()],
             ['genesis hash', txn.genesis_hash.lower()],
             ['note', f'{len(txn.note)} bytes'],
             ['receiver', txn.receiver.lower()], 
             ['amount (alg)', str(int(txn.amt/1000000))],
             ['close to', txn.close_remainder_to.lower()],
             ['sign', 'transaction']]

    return messages


txn_labels = {
    'review', 'txn type', 'sender', 'fee',
    'genesis id', 'genesis hash', 'note', 'receiver', 'amount', 'rekey to', 'close to', 'sign','cancel'
} 

conf_label = "sign"



def test_sign_msgpack_validate_display_with_rekey(dongle, payment_txn):
    """
    """
    payment_txn.rekey_to = "NWBZBIROXZQEETCDKX6IZVVBV4EY637KCIX56LE5EHIQERCTSDYGXWG6PU"
    
    decoded_txn = base64.b64decode(algosdk.encoding.msgpack_encode(payment_txn))

    with dongle.screen_event_handler(ui_interaction.confirm_on_lablel, txn_labels, conf_label):
        logging.info(decoded_txn)        
        _ = txn_utils.sign_algo_txn(dongle, decoded_txn)
        messages = dongle.get_messages()

    logging.info(messages)
    expected_messages = get_expected_messages(payment_txn)
    expected_messages.insert(3,['rekey to', payment_txn.rekey_to.lower()])
    logging.info(expected_messages)
    assert expected_messages == messages
    


def test_sign_msgpack_validate_display(dongle, payment_txn):
    """
    """
    decoded_txn = base64.b64decode(algosdk.encoding.msgpack_encode(payment_txn))
    with dongle.screen_event_handler(ui_interaction.confirm_on_lablel, txn_labels, conf_label):
        logging.info(decoded_txn)        
        _ = txn_utils.sign_algo_txn(dongle, decoded_txn)
        messages = dongle.get_messages()
    logging.info(messages)
    logging.info(get_expected_messages(payment_txn))
    assert get_expected_messages(payment_txn) == messages

    
    
def test_sign_msgpack_cancel_validate_display(dongle, payment_txn):
    """
    """
    decoded_txn = base64.b64decode(algosdk.encoding.msgpack_encode(payment_txn))
    with dongle.screen_event_handler(ui_interaction.confirm_on_lablel, txn_labels, "cancel"):
            with pytest.raises(speculos.CommException) as excinfo:
                _ = txn_utils.sign_algo_txn(dongle, decoded_txn)
            assert excinfo.value.sw == 0x6985
        


@pytest.mark.parametrize('account_id', [0,1,2,10,50])
def test_sign_msgpack_with_spcific_account(dongle, payment_txn, account_id):
    """
    """
    apdu = struct.pack('>BBBBBI', 0x80, 0x3, 0x0, 0x0,0x4, account_id)
    pubKey = dongle.exchange(apdu)

    decoded_txn = base64.b64decode(algosdk.encoding.msgpack_encode(payment_txn))
    with dongle.screen_event_handler(ui_interaction.confirm_on_lablel, txn_labels, conf_label):
        logging.info(decoded_txn)
        txnSig = txn_utils.sign_algo_txn_with_account(dongle, decoded_txn, account_id)

    assert len(txnSig) == 64
    verify_key = nacl.signing.VerifyKey(pubKey)
    verify_key.verify(smessage=b'TX' + decoded_txn, signature=txnSig)


def test_sign_msgpack_with_default_account(dongle, payment_txn):
    """
    """
    apdu = struct.pack('>BBBBB', 0x80, 0x3, 0x0, 0x0, 0x0)
    pubKey = dongle.exchange(apdu)

    decoded_txn = base64.b64decode(algosdk.encoding.msgpack_encode(payment_txn))
    with dongle.screen_event_handler(ui_interaction.confirm_on_lablel, txn_labels, conf_label):
        logging.info(decoded_txn)
        txnSig = txn_utils.sign_algo_txn(dongle, decoded_txn)

    assert len(txnSig) == 64
    verify_key = nacl.signing.VerifyKey(pubKey)
    verify_key.verify(smessage=b'TX' + decoded_txn, signature=txnSig)


def test_sign_msgpack_wrong_size_in_payload(dongle, payment_txn):
    """
    """
    with pytest.raises(speculos.CommException) as excinfo:
        dongle.exchange(struct.pack('>BBBBB10s' , 0x80, 0x8, 0x0, 0x0, 250, bytes(10)))
        
    assert excinfo.value.sw == 0x6a85

@pytest.mark.parametrize('chunk_size', [10, 20 ,50, 250])
def test_sign_msgpack_differnet_chunk_size(dongle, payment_txn, chunk_size):
    """
    """
    apdu = struct.pack('>BBBBB', 0x80, 0x3, 0x0, 0x0, 0x0)
    pubKey = dongle.exchange(apdu)


    decoded_txn= base64.b64decode(algosdk.encoding.msgpack_encode(payment_txn))

    with dongle.screen_event_handler(ui_interaction.confirm_on_lablel, txn_labels, conf_label):
        logging.info(decoded_txn)
        txnSig = txn_utils.sign_algo_txn(dongle, decoded_txn,chunk_size)

    assert len(txnSig) == 64
    verify_key = nacl.signing.VerifyKey(pubKey)
    verify_key.verify(smessage=b'TX' + decoded_txn, signature=txnSig)


def test_sign_txn_larger_then_internal_buffer(dongle, payment_txn):
    """
    """
    payment_txn.note = ("1"*800).encode()  
    decoded_txn = base64.b64decode(algosdk.encoding.msgpack_encode(payment_txn))

    with pytest.raises(speculos.CommException) as excinfo:    
        dongle.exchange(txn_utils.sign_algo_txn(dongle, decoded_txn))
        
    assert excinfo.value.sw == 0x6700


def test_sign_txn_long_field(dongle, payment_txn):
    """
    """      
    payment_txn.note = ("1"*500).encode()  
    decoded_txn = base64.b64decode(algosdk.encoding.msgpack_encode(payment_txn))
    with pytest.raises(speculos.CommException) as excinfo:
        dongle.exchange(txn_utils.sign_algo_txn(dongle, decoded_txn))
        
    assert excinfo.value.sw == 0x6e00


@pytest.mark.parametrize('account_id', [0, 1, 3, 7, 10, 42, 12345])
def test_sign_msgpack_with_valid_account_id(dongle, payment_txn, account_id):
    """
    """
    apdu = struct.pack('>BBBBBI', 0x80, 0x3, 0x0, 0x0, 0x4, account_id)
    pubKey = dongle.exchange(apdu)

    decoded_txn = base64.b64decode(algosdk.encoding.msgpack_encode(payment_txn))
    with dongle.screen_event_handler(ui_interaction.confirm_on_lablel, txn_labels, conf_label):
        logging.info(decoded_txn)
        txnSig = txn_utils.sign_algo_txn(dongle=dongle,
                               txn=struct.pack('>I', account_id) + decoded_txn,
                               p1=0x1)

    assert len(txnSig) == 64
    verify_key = nacl.signing.VerifyKey(pubKey)
    verify_key.verify(smessage=b'TX' + decoded_txn, signature=txnSig)


def test_sign_msgpack_returns_same_signature(dongle, payment_txn):
    """
    """
    decoded_txn = base64.b64decode(algosdk.encoding.msgpack_encode(payment_txn))
    with dongle.screen_event_handler(ui_interaction.confirm_on_lablel, txn_labels, conf_label):
        defaultTxnSig = txn_utils.sign_algo_txn(dongle, decoded_txn)
        

    with dongle.screen_event_handler(ui_interaction.confirm_on_lablel, txn_labels, conf_label):
        txnSig = txn_utils.sign_algo_txn(dongle=dongle,
                               txn=struct.pack('>I', 0x0) + decoded_txn,
                               p1=0x1)

    assert txnSig == defaultTxnSig


