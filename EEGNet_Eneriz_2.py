import numpy as np
import os
import json
from sklearn.model_selection import StratifiedKFold
import tensorflow as tf
from datetime import datetime
import matplotlib.pyplot as plt 


def EEGNet_Eneriz(
        nb_classes=4, ds=1, Chans=8, Samples=480,
        dropoutRate=0.0, kernLength=80, F1=4,
        D=2, F2=8, dropoutType='Dropout'):

    layers = tf.keras.layers

    # Selección del tipo de dropout
    if dropoutType == 'SpatialDropout2D':
        Drop = layers.SpatialDropout2D
    elif dropoutType == 'Dropout':
        Drop = layers.Dropout
    else:
        raise ValueError("dropoutType must be 'Dropout' or 'SpatialDropout2D'")

    input1 = layers.Input(shape=(Chans, Samples, 1))

    # Bloque 1
    block1 = layers.Conv2D(F1, (1, kernLength), padding='same',
                           use_bias=False)(input1)
    block1 = layers.LeakyReLU(negative_slope=0.4)(block1)

    block1 = layers.DepthwiseConv2D(
        (Chans, 1),
        use_bias=False,
        depth_multiplier=D,
        depthwise_constraint=tf.keras.constraints.max_norm(1.)
    )(block1)

    block1 = layers.LeakyReLU(negative_slope=0.5)(block1)
    block1 = layers.AveragePooling2D((1, 6 // ds))(block1)
    block1 = Drop(dropoutRate)(block1)

    # Bloque 2
    block2 = layers.SeparableConv2D(F2, (1, 16),
                                    use_bias=False,
                                    padding='same')(block1)
    block2 = layers.BatchNormalization()(block2)
    block2 = layers.LeakyReLU(negative_slope=0.6)(block2)
    block2 = layers.AveragePooling2D((1, 8))(block2)
    block2 = Drop(dropoutRate)(block2)

    # Clasificación
    flatten = layers.Flatten()(block2)
    dense = layers.Dense(nb_classes)(flatten)
    softmax = layers.Activation('softmax')(dense)

    return tf.keras.Model(inputs=input1, outputs=softmax)


def singleTrain (model, X_train, Y_train, X_val, Y_val, 
                 weightsFolder=None, lr_schedule=None, epochs = 100, batch_size = 16, verbose = 1,nb_classes=4,ds=1, Channels = 8, Samples = 480):

    #tf.random.set_seed(42) 
    
    # -------------------------
    # Cargar pesos si se pasan
    # -------------------------
    if weightsFolder is not None:
        model.load_weights(weightsFolder)
        print(f'Pesos cargados del archivo : {weightsFolder}')
    else :
        print(f'Los pesos se inicializan aleatoriamente')
    # -------------------------
    # Callbacks opcionales
    # -------------------------
    callbacks = []
    if lr_schedule is not None:
        lr_scheduler = tf.keras.callbacks.LearningRateScheduler(lr_schedule)
        callbacks.append(lr_scheduler)
        print(f'Usando Learning Rate Scheduler : {lr_schedule}')
    else : 
        print('Usando Learning Rate por defecto')


    history = model.fit(X_train, Y_train, batch_size = batch_size, epochs = epochs, 
                        verbose = verbose, validation_data=(X_val, Y_val), callbacks=callbacks)

    return model, history


def cvPartition (folds, samples, labels, subjects,
                  Channels=8, Samples=480, nb_classes=4):

    '''
    Samples shape: (8820, 8, 480)
    Labels shape: (8820,)
    Subjects shape: (8820,)
    '''

    X_cv5 =      np.zeros(shape = (folds, int(len(samples[:,0,0])/folds),Channels,Samples))  # [folds, total de samples / folds, canales, muestras por medida]
    labels_cv5 = np.zeros(shape = (folds, int(len(samples[:,0,0])/folds)))                   # [folds, total de samples / folds]
    Y_cv5 =      np.zeros(shape = (folds, int(len(samples[:,0,0])/folds),nb_classes))        # [folds, total de samples / folds, dimension extra por ser hotEncoded (numero de clases)]           
    subjects_cv5 = np.zeros(shape = (folds, int(len(samples[:,0,0])/folds)))                   # [folds, total de samples / folds]
    unique_labels = np.unique(labels)
    #print(f'Unique labels: {unique_labels}')

    for i in range(folds):

        #Asignamos a la primera componente de los vectores [fold] las muestras correspondientes a ese bloque ( total de samples / folds)
        X_cv5[i] = samples[ i*int(len(samples[:,0,0])/folds) : (i+1)*int(len(samples[:,0,0])/folds)] 
        labels_cv5[i] = labels[ i*int(len(samples[:,0,0])/folds) : (i+1)*int(len(samples[:,0,0])/folds)]
        Y_cv5[i]      = tf.keras.utils.to_categorical(labels_cv5[i], num_classes=nb_classes)
        subjects_cv5[i] = subjects[ i*int(len(samples[:,0,0])/folds) : (i+1)*int(len(samples[:,0,0])/folds)]
        #print(f' Equilibrio de clases: 0:{len(np.where(labels_cv5[i]==unique_labels[0])[0])} 1:{len(np.where(labels_cv5[i]==unique_labels[1])[0])} 2:{len(np.where(labels_cv5[i]==unique_labels[2])[0])} 3:{len(np.where(labels_cv5[i]==unique_labels[3])[0])}')
    
    
    #DEBUG
    
   
    #print(f'Y_cv5.shape :        {Y_cv5.shape}')
    #print(f'X_cv5.shape :        {X_cv5.shape}')
    #print(f'subjects_cv5.shape : {subjects_cv5.shape}')

    return X_cv5, Y_cv5, subjects_cv5


def cvTrain(folds,samples, labels, subjects,
             outputFolder=None,weights_folder=None, lr_schedule=None, epochs = 100, batch_size = 16, verbose = 1, Channels=8, Samples=480,nb_classes=4,ds=1):

    if samples.size == 0:
        print("El sujeto no existe")
        return
   
    if outputFolder is not None:
        # Crear carpeta de pesos si no existe, añadiendole el timestamp actual
        outputFolder = create_unique_folder(outputFolder)
 
    #Hacemos la partición en folds subsets
    X_cv, Y_cv, subjects_cv = cvPartition(folds,samples,labels,subjects,Channels,Samples,nb_classes)
    #Definimos los objetos con las accuracies de cada fold
    acc     = np.empty(folds, dtype=object)
    val_acc = np.empty(folds, dtype=object)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    for i_val in range(folds):

        #Asignamos los subsets de entrenamiento y validación correspondiente
        X_train        = np.concatenate([X_cv[i] for i in range(folds) if i != i_val])
        Y_train        = np.concatenate([Y_cv[i] for i in range(folds) if i != i_val])
        #subjects_train = np.concatenate([subjects_cv5[i] for i in range(5) if i != i_val])     no se usaban para nada
        X_val, Y_val, subjects_val     = X_cv[i_val], Y_cv[i_val], subjects_cv[i_val] 

        print( f'Fold {i_val}: sujetos validación: {np.min(np.unique(subjects_val))} - {np.max(np.unique(subjects_val))}')


        #Creamos un modelo nuevo para entrenar, con los mismos pesos aleatorios
        model_cv = EEGNet_Eneriz(nb_classes,ds,Channels,Samples)
        model_cv.compile(loss='categorical_crossentropy', optimizer=tf.keras.optimizers.Adam() , 
            metrics = ['accuracy'])
        
        #Si queremos entrenar con unos pesos iniciales concretos
        if(weights_folder!=None):
            model_cv.load_weights(weights_folder)
            print(f'Pesos cargados desde : {weights_folder}')

        #Llamamos a la función de entrenamiento individual
        fittedModel, fittedHistory = singleTrain(model_cv,X_train,Y_train,X_val,Y_val,lr_schedule=lr_schedule,
                                                 epochs = epochs, batch_size = batch_size, verbose = verbose,nb_classes= nb_classes,ds=ds, Channels = Channels, Samples = Samples,weightsFolder=weights_folder) 
        
        #Guardamos las métricas
        acc[i_val]      = fittedHistory.history['accuracy']
        val_acc[i_val]  = fittedHistory.history['val_accuracy']

        if outputFolder is not None:
            #Guardamos los pesos en una carpeta
            fittedModel.save_weights(os.path.join(outputFolder, f'pesos_fold{i_val:.0f}.weights.h5'))

        print(f'accuracy en train: {acc[i_val][-1]:.3f} || accuracy en val: {val_acc[i_val][-1]:.3f}')

    if outputFolder is not None:
        #Escribimos las metricas en la carpeta
        acc_array = np.vstack([np.array(fold, dtype=float) for fold in acc])
        np.savetxt(os.path.join(outputFolder,'acc.txt'), acc_array, fmt="%.4f", delimiter="\t")

        val_acc_array = np.vstack([np.array(fold, dtype=float) for fold in val_acc])
        np.savetxt(os.path.join(outputFolder,"valAcc.txt"), val_acc_array, fmt="%.4f", delimiter="\t")

        #Guardamos los parametros de entrenamiento por si acaso, la seed sería ideal tambien
        with open(os.path.join(outputFolder,'parametros.txt'), "w") as f:
            f.write(f"epochs = {epochs}\n")
            f.write(f"batch size = {batch_size}\n")
            f.write(f"batch size = {batch_size}\n")


    return acc, val_acc

'''
def subjectSpecificData(subjectSpecific, samples, labels, subjects):
    indexes = np.where(subjects==subjectSpecific)[0]
    
    #Es importante barajar los datos ahora, porque la funcion de cvPartition no barajea nada.
    rng = np.random.default_rng(seed=42) 
    rng.shuffle(indexes)

    return samples[indexes], labels[indexes],subjects[indexes]
'''

def subjectSpecificData(subjectSpecific, samples, labels, subjects):
    # Seleccionar índices del sujeto
    indexes = np.where(subjects == subjectSpecific)[0]

    # Crear generador determinista
    rng = np.random.default_rng(seed=42)

    # Separar índices por clase
    class_indices = {}
    for c in np.unique(labels):
        idx = indexes[labels[indexes] == c]
        rng.shuffle(idx)  # barajar cada clase de forma determinista
        class_indices[c] = idx

    # Intercalar: uno de cada clase por ronda
    intercalated = []
    max_len = max(len(v) for v in class_indices.values())

    for i in range(max_len):
        for c in sorted(class_indices.keys()):
            if i < len(class_indices[c]):
                intercalated.append(class_indices[c][i])

    intercalated = np.array(intercalated, dtype=np.int64)

    return samples[intercalated], labels[intercalated], subjects[intercalated]


def LoadDatabase(topFolder, Channels):

    if(Channels != 64):
        channelsInfo_file = r'C:\Users\Manuel Morato Miguel\Desktop\EEG\EEGNet\arl-eegmodels-master\channels_info.json'

        with open(channelsInfo_file, "r") as f:
            channelsInfo = json.load(f)

        indexes = channelsInfo[str(Channels)]["indexes"]
        print(f'Selected channels: {indexes}')    
        
        samples = np.load(os.path.join(topFolder,"samples.npy"))   # Datos EEG
        samples = samples*1000                                      # Los datos son microVoltios
        selectedSamples = samples[:,indexes,:]

        labels = np.load(os.path.join(topFolder,"labels.npy"))     # Etiquetas
        subjects = np.load(os.path.join(topFolder,"subjects.npy")) # IDs de sujetos
        
        return selectedSamples, labels, subjects

    else:
        samples = np.load(os.path.join(topFolder,"samples.npy"))   # Datos EEG
        samples = samples*1000                                      # Los datos son microVoltios
        labels = np.load(os.path.join(topFolder,"labels.npy"))     # Etiquetas
        subjects = np.load(os.path.join(topFolder,"subjects.npy")) # IDs de sujetos

        return samples,labels,subjects


def plotCvHistory(folds, dataFolder):

    acc_array = np.loadtxt(os.path.join(dataFolder, 'acc.txt'))
    valAcc_array = np.loadtxt(os.path.join(dataFolder,'valAcc.txt'))

    fig, ax = plt.subplots(1,2,sharey='all',figsize=(15,5))

    for fold, acc in enumerate(acc_array):
        ax[0].plot(np.arange(1,len(acc)+1,1),acc, label = f'Fold: {fold+1:.0f}', color = plt.cm.viridis(fold/folds))
        ax[1].plot(np.arange(1,len(acc)+1,1),valAcc_array[fold], label = f'Fold: {fold+1:.0f}', color = plt.cm.viridis(fold/folds))
    
    ax[0].set_title('Datos de Entrenamiento')
    ax[1].set_title('Datos de Validación')
    ax[0].set_xlabel('epochs')
    ax[1].set_xlabel('epochs')
    ax[0].legend()
    ax[1].legend()
    #Imprimir también el valor medio y la desviación
    acc_prom = np.sum(acc_array[:,-1])/folds
    acc_std=   np.std(acc_array[:,-1])
    ax[0].text(0.5, 0.1, f"acc (%): {100*acc_prom:.2f} + {100*acc_std:.2f}",
            transform=ax[0].transAxes,   # coordenadas relativas al eje (0-1)
            fontsize=12,
            verticalalignment='top', horizontalalignment='center',
            bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue", edgecolor="navy"))
    acc_prom = np.sum(valAcc_array[:,-1])/folds
    acc_std=   np.std(valAcc_array[:,-1])
    ax[1].text(0.5, 0.1, f"valAcc (%): {100*acc_prom:.2f} + {100*acc_std:.2f}",
            transform=ax[1].transAxes,   # coordenadas relativas al eje (0-1)
            fontsize=12,
            verticalalignment='top', horizontalalignment='center',
            bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue", edgecolor="navy"))
    


def create_unique_folder(base_path):
    """
    Crea una carpeta. Si ya existe, añade (1), (2), ... hasta encontrar un nombre libre.
    Devuelve la ruta final creada.
    """
    path = base_path

    if not os.path.exists(path):
        os.makedirs(path)
        return path

    counter = 1
    while True:
        new_path = f"{base_path} ({counter})"
        if not os.path.exists(new_path):
            os.makedirs(new_path)
            return new_path
        counter += 1
