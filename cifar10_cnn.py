'''Train a simple deep CNN on the CIFAR10 small images dataset.

GPU run command:
    THEANO_FLAGS=mode=FAST_RUN,device=gpu,floatX=float32 python cifar10_cnn.py

It gets down to 0.65 test logloss in 25 epochs, and down to 0.55 after 50 epochs.
(it's still underfitting at that point, though).

Note: the data was pickled with Python 2, and some encoding issues might prevent you
from loading it in Python 3. You might have to load it in Python 2,
save it in a different format, load it in Python 3 and repickle it.
'''

from __future__ import print_function
from keras.datasets import cifar10
from keras.preprocessing.image import ImageDataGenerator
from keras.models import Sequential
from keras.layers import Dense, Dropout, Activation, Flatten
from keras.layers import Convolution2D, MaxPooling2D, GaussianNoise, MaxoutDense
from keras.regularizers import l1, l2, activity_l1, activity_l2, l1l2
from keras.optimizers import SGD
from keras.utils import np_utils
import matplotlib.pyplot as plt
import optparse
import sys
import os


batch_size = 32
nb_classes = 10
nb_epoch = 100
data_augmentation = False

# input image dimensions
img_rows, img_cols = 32, 32
# the CIFAR10 images are RGB
img_channels = 3
sigma = 0.01
l1_weight = 0.5
l2_weight = 0.5

def parse_arg():
    parser = optparse.OptionParser('usage%prog [-l load parameterf from] [-d dump parameter to] [-e epoch] [-r src or tgt]')
    parser.add_option('-e', dest='epoch')
    parser.add_option('-a', dest='data_augmentation')
    parser.add_option('-n', dest='noise')
    parser.add_option('-m', dest='maxout')
    parser.add_option('-d', dest='dropout')
    parser.add_option('-l', dest='l1')
    parser.add_option('-r', dest='l2')

    (options, args) = parser.parse_args()
    return options

def main(nb_epoch=50, data_augmentation=False, noise=False, maxout=False, dropout=False, l1=False, l2=False):
    # l1 and l2 regularization shouldn't be true in the same time
    if l1 and l2:
        print("No need to run l1 and l2 regularization in the same time")
        quit()
    # print settings for this experiment
    print("number of epoch: {0}".format(nb_epoch))
    print("data augmentation: {0}".format(data_augmentation))
    print("noise: {0}".format(noise))
    print("maxout: {0}".format(maxout))
    print("dropout: {0}".format(dropout))
    print("l1: {0}".format(l1))
    print("l2: {0}".format(l2))
    # the data, shuffled and split between train and test sets
    (X_train, y_train), (X_test, y_test) = cifar10.load_data()
    print('X_train shape:', X_train.shape)
    print(X_train.shape[0], 'train samples')
    print(X_test.shape[0], 'test samples')

    # convert class vectors to binary class matrices
    Y_train = np_utils.to_categorical(y_train, nb_classes)
    Y_test = np_utils.to_categorical(y_test, nb_classes)

    model = Sequential()
    # try different kind of noise here
    if noise:
        model.add(GaussianNoise(sigma, input_shape=(img_channels, img_rows, img_cols)))
    model.add(Convolution2D(32, 3, 3, border_mode='same',
                            input_shape=(img_channels, img_rows, img_cols)))
    model.add(Activation('relu'))
    model.add(Convolution2D(32, 3, 3))
    model.add(Activation('relu'))
    model.add(MaxPooling2D(pool_size=(2, 2)))
    if dropout:
        model.add(Dropout(0.25))

    model.add(Convolution2D(64, 3, 3, border_mode='same'))
    model.add(Activation('relu'))
    model.add(Convolution2D(64, 3, 3))
    model.add(Activation('relu'))
    model.add(MaxPooling2D(pool_size=(2, 2)))
    if dropout:
        model.add(Dropout(0.25))

    model.add(Flatten())
    if maxout:
        model.add(MaxoutDense(512, nb_feature=4, init='glorot_uniform'))
    if not (l1 or l2):
        model.add(Dense(512))
    if l1:
        model.add(Dense(512),  W_regularizer=l1(l1_weight))
    elif l2:
        model.add(Dense(512),  W_regularizer=l2(l2_weight))

    model.add(Activation('relu'))
    if dropout:
        model.add(Dropout(0.5))
    model.add(Dense(nb_classes))
    model.add(Activation('softmax'))

    # let's train the model using SGD + momentum (how original).
    sgd = SGD(lr=0.01, decay=1e-6, momentum=0.9, nesterov=True)
    model.compile(loss='categorical_crossentropy',
                  optimizer=sgd,
                  metrics=['accuracy'])

    X_train = X_train.astype('float32')
    X_test = X_test.astype('float32')
    X_train /= 255
    X_test /= 255

    if not data_augmentation:
        his = model.fit(X_train, Y_train,
                  batch_size=batch_size,
                  nb_epoch=nb_epoch,
                  validation_split=0.2,
                  shuffle=True)
    else:
        # this will do preprocessing and realtime data augmentation
        datagen = ImageDataGenerator(
            featurewise_center=False,  # set input mean to 0 over the dataset
            samplewise_center=False,  # set each sample mean to 0
            featurewise_std_normalization=False,  # divide inputs by std of the dataset
            samplewise_std_normalization=False,  # divide each input by its std
            zca_whitening=False,  # apply ZCA whitening
            rotation_range=0,  # randomly rotate images in the range (degrees, 0 to 180)
            width_shift_range=0.1,  # randomly shift images horizontally (fraction of total width)
            height_shift_range=0.1,  # randomly shift images vertically (fraction of total height)
            horizontal_flip=True,  # randomly flip images
            vertical_flip=False)  # randomly flip images

        # compute quantities required for featurewise normalization
        # (std, mean, and principal components if ZCA whitening is applied)
        datagen.fit(X_train)

        # fit the model on the batches generated by datagen.flow()
        his = model.fit_generator(datagen.flow(X_train, Y_train,
                            batch_size=batch_size),
                            samples_per_epoch=X_train.shape[0],
                            nb_epoch=nb_epoch,
                            validation_split=0.2)

    # evaluate our model
    score = model.evaluate(X_test, Y_test, verbose=0)
    print('Test score:', score[0])
    print('Test accuracy:', score[1])

    # wirte test accuracy to a file
    output_file_name = './output/train_val_loss_with_dropout_epochs_{0}_data_augmentation_{1}_noise_{2}_maxout_{3}_dropout_{4}_l1_{5}_l2_{6}.txt'.format(nb_epoch, data_augmentation, noise, maxout, dropout, l1, l2)
    print(output_file_name)
    with open(output_file_name, "w") as text_file:
        text_file.write('Test score: {}'.format(score[0]))
        text_file.write('\n')
        text_file.write('Test accuracy: {}'.format(score[1]))
    text_file.close()

    # visualize training history
    train_loss = his.history['loss']
    val_loss = his.history['val_loss']
    plt.plot(range(1, len(train_loss)+1), train_loss, color='blue', label='train loss')
    plt.plot(range(1, len(val_loss)+1), val_loss, color='red', label='val loss')
    plt.legend(loc="upper left", bbox_to_anchor=(1,1))
    plt.xlabel('#epoch')
    plt.ylabel('loss')
    # @TODO what's the deal around here ~"~"?
    output_fig_name = './output/train_val_loss_with_dropout_epochs_{0}_data_augmentation_{1}_noise_sigma_0.01_{2}_maxout_{3}_dropout_{4}_l1_weight_0.05_{5}_l2_wieght_0.05_{6}.png'.format(nb_epoch, data_augmentation, noise, maxout, dropout, l1, l2)
    plt.savefig(output_fig_name, dpi=300)
    plt.show()

if __name__ == '__main__':
    opts = parse_arg()
    kwargs = {}
    if len(sys.argv) > 1:
        kwargs['nb_epoch'] = int(opts.epoch)
        kwargs['data_augmentation'] = True if opts.data_augmentation == 'True' else False
        kwargs['noise'] = True if opts.noise == 'True' else False
        kwargs['maxout'] = True if opts.maxout == 'True' else False
        kwargs['dropout'] = True if opts.dropout == 'True' else False
        kwargs['l1'] = True if opts.l1 == 'True' else False
        kwargs['l2'] = True if opts.l2 == 'True' else False

    main(**kwargs)
