import argparse
import os
import numpy as np
import random
import torch


def set_defaults():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    # comet_ml configs
    parser.add_argument('--comet_key', type=str, default='');
    parser.add_argument('--comet_project', type=str, default='');
    parser.add_argument('--comet_workspace', type=str, default='');

    # data files configs
    parser.add_argument('--data_root', default='.', help='path to dataset')
    parser.add_argument('--pct_val', type=float, default=0.20, help='')
    parser.add_argument('--pct_test', type=float, default=0.20, help='')

    # audio data configs
    parser.add_argument('--signal_sr', type=int, default=16000, help='')
    parser.add_argument('--signal_len', type=float, default=1, help='')
    parser.add_argument('--nmfcc', type=int, default=40, help='')
    parser.add_argument('--nfilter', type=int, default=81, help='')
    parser.add_argument('--nsilence', type=int, default=-1, help='')

    # experiment configs
    parser.add_argument('--name', type=str, default='untitled', help='name of the experiment')
    parser.add_argument('--outf', default='./output', help='folder to output images and model checkpoints')
    parser.add_argument('--seed', default=-1, type=int, help='manual seed')
    parser.add_argument('--frq_log', type=int, default=2, help='frequency of showing training results on console')
    parser.add_argument('--debug', type=int, default=32 * 4, help='')
    parser.add_argument('--test', action='store_true', default=False, help='load weights and run on test set')
    parser.add_argument('--weights_path', type=str, default=None, help='')

    # training configs
    parser.add_argument('--weight_decay', type=int, default=1e-5, help='number of epochs to train for')
    parser.add_argument('--nepoch', type=int, default=2, help='number of epochs to train for')
    parser.add_argument('--batchsize', type=int, default=32, help='input batch size')
    parser.add_argument('--metric', type=str, default='acc', help='')
    parser.add_argument('--lr', type=float, default=0.01, help='learning rate')
    parser.add_argument('--momentum', type=int, default=0.9, help='')
    parser.add_argument('--beta1', type=float, default=0.9, help='')
    parser.add_argument('--optimizer', type=str, default='sgd', help='adam | sgd')
    parser.add_argument('--scheduler', type=str, default='none', help='auto | set | none')

    # model architecture
    parser.add_argument('--model', type=str, default='ResNet');
    parser.add_argument('--dropout', type=float, default=0.5);
    parser.add_argument('--nlayer', type=int, default=8);
    parser.add_argument('--nchannel', type=int, default=19);
    parser.add_argument('--res_pool', type=tuple, default=(1, 1));
    parser.add_argument('--use_dilation', action='store_true', default=False);


    return parser.parse_args();


def get_args():
    args = set_defaults();

    expr_dir = os.path.join(args.outf, args.name)
    if not os.path.isdir(expr_dir): os.makedirs(expr_dir)

    if args.seed != -1:
        print('using manual seed: {}'.format(args.seed));
        random.seed(args.seed)
        np.random.seed(args.seed)
        torch.manual_seed(args.seed)
        torch.cuda.manual_seed_all(args.seed)
        torch.backends.cudnn.deterministic = True

    return args
