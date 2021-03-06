import torch
import numpy as np
import os
from scipy.io import wavfile
import torchaudio


from src import utils
from src import transforms
from src.ClassDict import ClassDict
from src import load
import random

from comet_ml import Experiment
from src.configs import get_args
from src.data import get_dataloader
from src.trainer import ModelTrainer
from src.model import *

import pandas as pd


class ASCDataset(torch.utils.data.Dataset):

    def __init__(self, data_root, dataset, transform, s_transform, nsilence, signal_samples, signal_sr, noise_pkg):
        super().__init__()

        self.transform = transform
        self.s_transform = s_transform
        self.data_root = data_root
        self.signal_samples = signal_samples
        self.signal_sr = signal_sr

        dataset = list(zip(*dataset))
        self.audio_files = list(dataset[0])
        self.audio_labels = dataset[1]
        self.audio_labels = [ClassDict.getId(name) for name in self.audio_labels]

        if nsilence == -1:
            nsilence = len(self.audio_files) // ClassDict.len()

        self.nsilence = nsilence
        self.silence_label = ClassDict.len()

        self.nfl, self.npd = utils.get_noise_files(noise_pkg, signal_sr)
        self.noise_pkg = noise_pkg

        self.cache = []
        for idx in range(len(self.audio_files)):
            file_path = os.path.join(self.data_root, self.audio_files[idx])
            x = self.load_path(file_path)
            self.cache.append(x)

        self.s_cache = {}
        for file_name in self.nfl:
            file_path = os.path.join(self.noise_pkg, file_name)
            signal = self.load_path(file_path)
            self.s_cache[file_name] = signal

    def load_silence(self):
        file_name = np.random.choice(self.nfl, p=self.npd)
        # file_path = os.path.join(self.noise_pkg, file_name)
        # signal = self.load_path(file_path)
        signal = self.s_cache[file_name]
        start_index = np.random.randint(0, signal.size()[0] - self.signal_samples)
        silence = signal[start_index : start_index + self.signal_samples]

        tensor = self.s_transform(silence)
        return tensor

    def load_path(self, path):
        x, sr = torchaudio.load(path)
        x = x.squeeze()
        return x

    def load_audio(self, idx):
        # file_path = os.path.join(self.data_root, self.audio_files[idx])
        # x = self.load_path(file_path)
        x = self.cache[idx]
        tensor = self.transform(x)
        return tensor

    def __getitem__(self, index):
        if index >= len(self.audio_labels):
            return self.load_silence(), self.silence_label
        else:
            return self.load_audio(index), self.audio_labels[index]

    def __len__(self):
        return len(self.audio_labels) + self.nsilence


def get_transform(args):

    melkwargs = {
        'n_mels': args.nfilt,
        'n_fft': args.nfft,
        'win_length': int(args.winlen * args.signal_sr),
        'hop_length': int(args.winstep * args.signal_sr),
    }
    args.signal_samples = int(args.signal_sr * args.signal_len)

    args.signal_width = int(np.ceil((args.signal_len - args.winlen) / args.winstep) + 1)
    if args.features_name.lower() == 'logfbes':
        features = transforms.Compose([
            transforms.LogFBEs(args.signal_sr, args.winlen, args.winstep, args.nfilt,
                               args.nfft, args.preemph),
            transforms.ToTensor(),
            ])
        args.nfeature = args.nfilt
        args.signal_width = int(np.ceil((args.signal_len - args.winlen) / args.winstep) + 1)
    elif args.features_name.lower() == 'mfccs':
        features = transforms.Compose([
            transforms.MFCCs(args.signal_sr, args.winlen, args.winstep, args.numcep, args.nfilt,
                             args.nfft, args.preemph, args.ceplifter),
            transforms.ToTensor(),
            ])
        args.nfeature = args.numcep
        args.signal_width = int(np.ceil((args.signal_len - args.winlen) / args.winstep) + 1)
    elif args.features_name.lower() == 'ta.mfccs':
        features = transforms.Compose([
            # transforms.ToTensor(),
            torchaudio.transforms.MFCC(sample_rate=args.signal_sr, n_mfcc=args.numcep, melkwargs=melkwargs),
        ])
        args.nfeature = args.numcep
        args.signal_width = 1 + args.signal_samples // melkwargs['hop_length']
        # args.signal_width = 81;
    elif args.features_name.lower() == 'ta.logfbes':
        log_offset = 1e-6
        features = transforms.Compose([
            # transforms.ToTensor(),
            torchaudio.transforms.MelSpectrogram(sample_rate=args.signal_sr, **melkwargs),
            transforms.Lambda(lambda t: torch.log(t + log_offset)),
        ])
        args.nfeature = args.nfilt
        args.signal_width = 1 + args.signal_samples // melkwargs['hop_length']
        # args.signal_width = 81;
    else:
        raise Exception('--features_name should be one of {LogFBEs | MFCCs | ta.MFCCs | ta.LogFBEs}')

    # Composing transforms
    test_trasform = transforms.Compose([
        features,
        transforms.Lambda(lambda x: x.unsqueeze(0)),
    ])

    silence_transform = transforms.Compose([
        transforms.Lambda(lambda x: x * random.uniform(0.0, args.silence_vol)),
        test_trasform,
    ])

    args.signal_samples = int(args.signal_sr * args.signal_len)
    args.bkg_noise_path = 'background_noise'

    train_transform = transforms.Compose([
        # transforms.TimeShifting2(shift_min=args.shift_min, shift_max=args.shift_max),
        # transforms.RandomApplyTransform(p=args.p_transform, transform=transforms.AddNoise3(
        #     os.path.join(args.data_root, args.bkg_noise_path),
        #     args.noise_vol, args.signal_samples, args.signal_sr)),
        test_trasform,
        # torchaudio.transforms.TimeMasking(args.mask_time),
        # torchaudio.transforms.TimeMasking(args.mask_time),
        # torchaudio.transforms.FrequencyMasking(args.mask_freq),
    ])

    return {'train': train_transform, 'val': test_trasform, 'test': test_trasform}, silence_transform


def main(args):
    args.nclass = ClassDict.len() + (args.nsilence != 0)
    splits = ['train', 'val', 'test']

    transform, s_transform = get_transform(args)

    dataset = utils.read_splits(args.data_root)

    if args.debug != -1:
        dataset = {split: dataset[split][:args.debug] for split in splits}

    dataset = {split: ASCDataset(args.data_root, dataset[split], transform[split], s_transform, args.nsilence,
                                 args.signal_samples, args.signal_sr, os.path.join(args.data_root, args.bkg_noise_path))
               for split in splits}

    for split in splits:
        columns = ['f_%04d' % i for i in range(99 * 12)] + ['label']
        # print(columns)
        df = pd.DataFrame(columns=columns)
        lst = []
        for idx in range(len(dataset[split])):
            features, cls = dataset[split][idx]
            features = features.numpy()
            features = features.squeeze()
            features = features[:, 1:]
            features = features.flatten()
            features = list(features) + [ClassDict.getName(cls)]
            # features = pd.DataFrame(features)
            # print(features)
            # print(features.shape)
            # df.append(features)
            # print(df.shape)
            lst.append(features)
        df = pd.DataFrame(lst, columns=columns)
        # print(df)
        df.to_csv(args.data_root + split + '_features.csv', index=False)


if __name__ == '__main__':
    args = get_args()
    args.data_root = '../assets/ASC_data/'
    args.features_name = 'MFCCs'
    args.debug = -1
    main(args)
