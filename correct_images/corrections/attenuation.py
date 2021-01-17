import numpy as np
import joblib
from correct_images.tools.curve_fitting import curve_fitting
from correct_images.tools.joblib_tqdm import tqdm_joblib
from tqdm import tqdm, trange


def attenuation_correct(img: np.ndarray,
                        altitude: np.ndarray,
                        atn_crr_params: np.ndarray,
                        gain: np.ndarray) -> np.ndarray:
    """ apply attenuation coefficients to an input image

    Parameters
    -----------
    img : numpy.ndarray
        input image
    altitude :
        distance matrix corresponding to the image
    atn_crr_params : numpy.ndarray
        attenuation coefficients
    gain : numpy.ndarray
        gain value for the image

    Returns
    -------
    numpy.ndarray
        Corrected image
    """
    # attenuation correction and gains matrices start with the channel
    # so we need to remove that first layer
    # (e.g. [1, 1024, 1280, 3] -> [1024, 1280, 3]])
    atn_crr_params = atn_crr_params.squeeze()

    img_float32 = img.astype(np.float32)
    gain = gain.squeeze()
    img_float32 = (
        (
            gain
            / (
                atn_crr_params[:, :, 0] * np.exp(atn_crr_params[:, :, 1] * altitude)
                + atn_crr_params[:, :, 2]
            )
        )
        * img_float32
    )
    return img_float32


def attenuation_correct_memmap(image_memmap: np.ndarray,
                               distance_memmap: np.ndarray,
                               attenuation_parameters: np.ndarray,
                               gains: np.ndarray) -> np.ndarray:
        """Apply attenuation corrections to an image memmap

        Parameters
        -----------
        image_memmap : numpy.ndarray
            input image memmap
        distance_memmap : numpy.ndarray
            input distance memmap
        attenuation_parameters : numpy.ndarray
            attenuation coefficients
        gains : numpy.ndarray
            gain values for the image


        Returns
        -------
        numpy.ndarray
            Resulting images after applying attenuation correction
        """
        for i_img in trange(image_memmap.shape[0]):
            # memmap data can not be updated in joblib .
            image_memmap[i_img, ...] = attenuation_correct(
                image_memmap[i_img, ...],
                distance_memmap[i_img, ...],
                attenuation_parameters,
                gains,
            )
        return image_memmap


# compute gain values for each pixel for a targeted altitude using the attenuation parameters
def calculate_correction_gains(target_altitude : np.ndarray,
                               attenuation_parameters : np.ndarray,
                               image_height : int, 
                               image_width : int, 
                               image_channels : int) -> np.ndarray:
    """Compute correction gains for an image

    Parameters
    -----------
    target_altitude : numpy.ndarray
        target distance for which the images will be corrected
    attenuation_parameters : numpy.ndarray
        attenuation coefficients

    Returns
    -------
    numpy.ndarray
        The correction gains
    """

    image_correction_gains = np.empty(
        (image_channels, image_height, image_width), dtype=np.float64
    )

    for i_channel in range(image_channels):

        #attenuation_parameters = attenuation_parameters.squeeze()
        correction_gains =  (
            attenuation_parameters[i_channel, :, :, 0]
            * np.exp(attenuation_parameters[i_channel, :, :, 1] * target_altitude)
            + attenuation_parameters[i_channel, :, :, 2]
        )
        image_correction_gains[i_channel] = correction_gains
    return image_correction_gains


# calculate image attenuation parameters
def calculate_attenuation_parameters(
        images, distances, image_height, image_width, image_channels
):
    """Compute attenuation parameters for all images

    Parameters
    -----------
    images : numpy.ndarray
        image memmap reshaped as a vector
    distances : numpy.ndarray
        distance memmap reshaped as a vector
    image_height : int
        height of an image
    image_width : int
        width of an image

    Returns
    -------
    numpy.ndarray
        attenuation_parameters
    """

    image_attenuation_parameters = np.empty(
        (image_channels, image_height, image_width, 3), dtype=np.float64
    )

    for i_channel in range(image_channels):
        with tqdm_joblib(tqdm(desc="Curve fitting", total=image_height * image_width)) as progress_bar:
            results = joblib.Parallel(n_jobs=-2, verbose=0)(
                [
                    joblib.delayed(curve_fitting)(np.array(distances[:, i_pixel]),
                                                np.array(images[:, i_pixel, i_channel]))
                    for i_pixel in range(image_height * image_width)
                ]
            )

            attenuation_parameters = np.array(results)
            attenuation_parameters = attenuation_parameters.reshape(
                [image_height, image_width, 3]
            )
        image_attenuation_parameters[i_channel] = attenuation_parameters
        
    return image_attenuation_parameters


