# -*- coding: utf-8 -*-
"""
Created on Tue Jun 18 09:16:18 2024

@author: Paul
"""

import numpy as np

def helmert_transformation_3d(source_points_polar, target_points):
    """
    Perform Helmert transformation (3D) to align source_points with target_points.
    
    Parameters:
    source_points (np.array): Source points array of shape (n_points, 3)
    target_points (np.array): Target points array of shape (n_points, 3)
    
    Returns:
    transformed_points (np.array): Transformed source points array of shape (n_points, 3)
    transformation_params (dict): Dictionary containing scale, rotation matrix, and translation vector
    residuals (np.array): Residuals array of shape (n_points,)
    """
    
    source_points = polar_to_cartesian(source_points_polar)
    
    # Compute centroids of both point sets
    centroid_source = np.mean(source_points, axis=0)
    centroid_target = np.mean(target_points, axis=0)

    # Center the points
    centered_source = source_points - centroid_source
    centered_target = target_points - centroid_target

    # Singular Value Decomposition (SVD)
    U, S, Vt = np.linalg.svd(np.dot(centered_source.T, centered_target))
    
    # Compute rotation matrix
    R = np.dot(U, Vt)

    # Compute scale
    scale = np.sum(S) / np.sum(centered_source ** 2)
    
    # Compute translation
    translation = centroid_target - scale * np.dot(centroid_source, R)

    # Transform the source points
    transformed_points = scale * np.dot(source_points, R) + translation

    # Calculate residuals
    residuals = np.linalg.norm(target_points - transformed_points, axis=1)

    # Return the transformed points, transformation parameters, and residuals
    transformation_params = {
        'scale': scale,
        'rotation_matrix': R,
        'translation_vector': translation
    }

    return transformed_points, transformation_params, residuals

def polar_to_cartesian(polar_points):
    """
    Convert polar coordinates to cartesian coordinates.
    
    Parameters:
    polar_points (np.array): Polar points array of shape (n_points, 3) [r, theta, z]
    
    Returns:
    cartesian_points (np.array): Cartesian points array of shape (n_points, 3)
    """
    k_0 = 0.060
    
    cartesian_points = np.zeros_like(polar_points)

    phi = np.radians(polar_points[:,0] * 0.9)
    theta = np.radians(polar_points[:,1] * 0.9)
    r = polar_points[:,2] + k_0
    #print(f"Theta: {theta} Phi: {phi} r: {r}")
    cartesian_points[:, 0] = r * np.sin(theta) * np.sin(phi) # Y
    cartesian_points[:, 1] = r * np.sin(theta) * np.cos(phi) # X
    cartesian_points[:, 2] = r * np.cos(theta) # Z
    return cartesian_points

def transform_measurement(measurements_polar, params):
    """
    Transform polar measurements to cartesian coordinates.
    
    Parameters:
    measurements_polar (np.array): Polar points array of shape (n_points, 3) [phi, theta, r]
    params (dict): Dictionary containing scale, rotation matrix, and translation vector
    
    Returns:
    transformed_mesaurements (np.array): Transformed measurements points array of shape (n_points, 3)

    """
    measurements = polar_to_cartesian(measurements_polar)
    
    scale = params['scale']
    R = params['rotation_matrix']
    translation = params['translation_vector']
    
    transformed_measurements = scale * np.dot(measurements, R) + translation
    return transformed_measurements

# # Beispiel: Bekannte Referenzpunkte (Zielpunkte) in globalen Koordinaten (X,Y,Z)
# target_points = np.array([
#     [2.2446,2.7253,0.1361],  
#     [-0.0490,-2.1568,0.5939],  
#     [-3.1987,-0.2907,0.8656],
#     [-1.6326,4.0551,-0.2797]
# ])

# # Gemessene Punkte (Quellpunkte) mit dem Tachymeter
# source_points_polar = np.array([
#     [62.26,108.53,4.3983],   # Beispielkoordinate für die Z-Achse: 16
#     [184.38,132.33,2.4252],  # Beispielkoordinate für die Z-Achse: 45
#     [309.73,131.25,2.7067],
#     [400.04,100.13,4.3621]# Beispielkoordinate für die Z-Achse: 59  # Beispielkoordinate für die Z-Achse: 59
# ])

# measurements_polar = np.array([
#     [0.26,0.87,2.3993] 
# ])

# #print(source_points)
# # Berechnung der Helmert-Transformation
# transformed_points, params, residuals = helmert_transformation_3d(source_points_polar, target_points)
# #print("Transformierte Punkte:\n", transformed_points)
# #print("Transformationsparameter:\n", params)
# print("Residuen:\n", residuals)

# transformed_measurements = transform_measurement(measurements_polar, params)

# #print("Transformierte Messwerte:\n", transformed_measurements)
