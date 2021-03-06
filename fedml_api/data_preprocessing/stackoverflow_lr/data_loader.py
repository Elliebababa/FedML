import logging

import h5py
import torch
import random
import numpy as np
import torch.utils.data as data
import utils

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.INFO)

client_map_train = None
client_map_test = None
DEFAULT_TRAIN_CLINETS_NUM = 342477
DEFAULT_TEST_CLIENTS_NUM = 204088
DEFAULT_BATCH_SIZE = 100
train_file_path = '../../../data/stackoverflow/datasets/stackoverflow_train.h5'
test_file_path = '../../../data/stackoverflow/datasets/stackoverflow_test.h5'
heldout_file_path = '../../../data/stackoverflow/datasets/stackoverflow_held_out.h5'

# group name defined by tff in h5 file
_EXAMPLE = 'examples'
_TOKENS = 'tokens'
_TITLE = 'title'
_TAGS = 'tags'


def get_client_map(client_map, client_id=None, client_num=None):
    if client_map == None:
        random.shuffle(client_id)
        client_map = {
            k: [client_id[i] for i in range(k, len(client_id), client_num)]
            for k in range(client_num)
        }
    return client_map


def get_dataloader(dataset, data_dir, train_bs, test_bs, client_idx=None):
    train_h5 = h5py.File(train_file_path, 'r')
    test_h5 = h5py.File(test_file_path, 'r')
    if client_idx is None:
        client_ids_train = list(train_h5[_EXAMPLE].keys())
        client_ids_test = list(test_h5[_EXAMPLE].keys())
    else:
        client_ids_train = get_client_map(client_map_train)[client_idx]
        client_ids_test = get_client_map(client_map_test)[client_idx]

    train_x = []
    train_y = []
    test_x = []
    test_y = []
    for client_id in client_ids_train:
        raw_tokens = train_h5[_EXAMPLE][client_id][_TOKENS][()]
        raw_tokens = [x.decode('utf8') for x in raw_tokens]
        raw_title = train_h5[_EXAMPLE][client_id][_TITLE][()]
        raw_title = [x.decode('utf8') for x in raw_title]
        raw_x = [' '.join(pair) for pair in zip(raw_tokens, raw_title)]
        raw_y = [
            x.decode('utf8') for x in train_h5[_EXAMPLE][client_id][_TAGS][()]
        ]
        train_x.extend(utils.preprocess_inputs(raw_x))
        train_y.extend(utils.preprocess_targets(raw_y))
    for client_id in client_ids_test:
        raw_tokens_test = test_h5[_EXAMPLE][client_id][_TOKENS][()]
        raw_tokens_test = [x.decode('utf8') for x in raw_tokens_test]
        raw_title_test = test_h5[_EXAMPLE][client_id][_TITLE][()]
        raw_title_test = [x.decode('utf8') for x in raw_title_test]
        raw_x_test = [
            ' '.join(pair) for pair in zip(raw_tokens_test, raw_title_test)
        ]
        raw_y_test = [
            x.decode('utf8') for x in test_h5[_EXAMPLE][client_id][_TAGS][()]
        ]
        test_x.extend(utils.preprocess_inputs(raw_x_test))
        test_y.extend(utils.preprocess_targets(raw_y_test))
    train_x, train_y = np.asarray(train_x), np.asarray(train_y)
    test_x, test_y = np.asarray(test_x), np.asarray(test_y)
    train_ds = data.TensorDataset(torch.tensor(train_x[:, :]),
                                  torch.tensor(train_y[:]))
    test_ds = data.TensorDataset(torch.tensor(test_x[:, :]),
                                 torch.tensor(test_y[:]))
    train_dl = data.DataLoader(dataset=train_ds,
                               batch_size=train_bs,
                               shuffle=True,
                               drop_last=False)
    test_dl = data.DataLoader(dataset=test_ds,
                              batch_size=test_bs,
                              shuffle=True,
                              drop_last=False)

    train_h5.close()
    test_h5.close()
    return train_dl, test_dl


def load_partition_data_distributed_federated_stackoverflow(
        process_id, dataset, data_dir, client_number = None, batch_size = DEFAULT_BATCH_SIZE):
    
    client_number_train = client_number_test = client_number
    if client_number is None:
        client_number_train = DEFAULT_TRAIN_CLINETS_NUM
        client_number_test = DEFAULT_TEST_CLIENTS_NUM

    # get global dataset
    if process_id == 0:
        train_data_global, test_data_global = get_dataloader(
            dataset, data_dir, batch_size, batch_size, process_id - 1)
        train_data_num = len(train_data_global)
        test_data_num = len(test_data_global)
        logging.info("train_dl_global number = " + str(train_data_num))
        logging.info("test_dl_global number = " + str(test_data_num))
        train_data_local = None
        test_data_local = None
        local_data_num = 0
    else:
        # get local dataset
        train_h5 = h5py.File(train_file_path, 'r')
        test_h5 = h5py.File(test_file_path, 'r')
        global client_map_train, client_map_test
        client_map_train = get_client_map(client_map_train,
                                          list(train_h5[_EXAMPLE].keys()),
                                          client_number_train)
        client_map_test = get_client_map(client_map_test,
                                         list(test_h5[_EXAMPLE].keys()),
                                         client_number_test)
        train_h5.close()
        test_h5.close()
        train_data_local, test_data_local = get_dataloader(
            dataset, data_dir, batch_size, batch_size, process_id - 1)
        train_data_num = local_data_num = len(train_data_local) + len(
            test_data_local)
        logging.info("rank = %d, local_sample_number = %d" %
                     (process_id, local_data_num))
        train_data_global = None
        test_data_global = None
    return train_data_num, train_data_global, test_data_global, local_data_num, train_data_local, test_data_local


def load_partition_data_federated_stackoverflow(dataset, data_dir, client_number = None, batch_size = DEFAULT_BATCH_SIZE):
    
    client_number_train = client_number_test = client_number
    if client_number is None:
        client_number_train = DEFAULT_TRAIN_CLINETS_NUM
        client_number_test = DEFAULT_TEST_CLIENTS_NUM
        
    train_data_global, test_data_global = get_dataloader(
        dataset, data_dir, batch_size, batch_size)
    train_data_num = len(train_data_global)
    test_data_num = len(test_data_global)

    # get local dataset
    data_local_num_dict = dict()
    train_data_local_dict = dict()
    test_data_local_dict = dict()
    train_h5 = h5py.File(train_file_path, 'r')
    test_h5 = h5py.File(test_file_path, 'r')
    global client_map_train, client_map_test
    client_map_train = get_client_map(client_map_train,
                                      list(train_h5[_EXAMPLE].keys()),
                                      client_number_train)
    client_map_test = get_client_map(client_map_test,
                                     list(test_h5[_EXAMPLE].keys()),
                                     client_number_test)
    train_h5.close()
    test_h5.close()

    for client_idx in range(client_number):

        train_data_local, test_data_local = get_dataloader(
            dataset, data_dir, batch_size, batch_size, client_idx)
        local_data_num = len(train_data_local) + len(test_data_local)
        data_local_num_dict[client_idx] = local_data_num
        logging.info("client_idx = %d, local_sample_number = %d" %
                     (client_idx, local_data_num))
        logging.info(
            "client_idx = %d, batch_num_train_local = %d, batch_num_test_local = %d"
            % (client_idx, len(train_data_local), len(test_data_local)))
        train_data_local_dict[client_idx] = train_data_local
        test_data_local_dict[client_idx] = test_data_local

    return train_data_num, test_data_num, train_data_global, test_data_global, \
        data_local_num_dict, train_data_local_dict, test_data_local_dict


if __name__ == "__main__":
    #load_partition_data_federated_stackoverflow(None, None, 100, 128)
    train_data_num, train_data_global, test_data_global, local_data_num, train_data_local, test_data_local = load_partition_data_distributed_federated_stackoverflow(
        2, None, None, 300000, 128)
    print(train_data_local, test_data_local)
