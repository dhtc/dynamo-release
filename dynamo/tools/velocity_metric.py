import numpy as np
from scipy.stats import pearsonr
from scipy.spatial.distance import cosine
from scipy.sparse import issparse
from .connectivity import umap_conn_indices_dist_embedding, mnn_from_list
from .utils import get_finite_inds


def cell_wise_confidence(adata, ekey='X', vkey='velocity_S', method='jaccard'):
    """ Calculate the cell-wise velocity confidence metric.

    Parameters
    ----------
        adata: :class:`~anndata.AnnData`
            an Annodata object.
        ekey: `str` (optional, default `M_s`)
            The dictionary key that corresponds to the gene expression in the layer attribute. By default, it is the
            smoothed expression
            `M_s`.
        vkey: 'str' (optional, default `velocity`)
            The dictionary key that corresponds to the estimated velocity values in layers attribute.
        method: `str` (optional, default `jaccard`)
            Which method will be used for calculating the cell wise velocity confidence metric. By default it uses
            `jaccard` index, which measures how well each velocity vector meets the geometric constraints defined by the
            local neighborhood structure. Jaccard index is calculated as the fraction of the number of the intersected
            set of nearest neighbors from each cell at current expression state (X) and that from the future expression
            state (X + V) over the number of the union of this two sets. The `cosine` or `correlation` method is similar
            to that used by scVelo (https://github.com/theislab/scvelo).

    Returns
    -------
        Adata: :class:`~anndata.AnnData`
            Returns an updated `~anndata.AnnData` with `.obs.confidence` as the cell-wise velocity confidence.
    """

    X, V = (adata.X, adata.layers[vkey]) if ekey is 'X' else (adata.layers[ekey], adata.layers[vkey])
    n_neigh, X_neighbors = adata.uns['neighbors']['params']['n_neighbors'], adata.uns['neighbors']['connectivities']

    finite_inds = get_finite_inds(V, 0)
    X, V = X[:, finite_inds], V[:, finite_inds]
    if method == 'jaccard':
        V_neighbors, _, _, _ = umap_conn_indices_dist_embedding(X + V, n_neighbors=n_neigh)

        union_ = X_neighbors + V_neighbors > 0
        intersect_ = mnn_from_list([X_neighbors, V_neighbors]) > 0

        confidence = (intersect_.sum(1) / union_.sum(1)).A1 if issparse(X) else intersect_.sum(1) / union_.sum(1)

    elif method == 'cosine':
        indices = adata.uns['neighbors']['indices']
        confidence = np.zeros(adata.n_obs)
        for i in range(adata.n_obs):
            neigh_ids = indices[i]
            confidence[i] = np.mean([cosine(X[i].A.flatten(), V[j][0].A.flatten()) for j in neigh_ids])

    elif method == 'correlation':
        indices = adata.uns['neighbors']['indices']
        confidence = np.zeros(adata.n_obs)
        for i in range(adata.n_obs):
            neigh_ids = indices[i]
            confidence[i] = np.mean([pearsonr(X[i].A.flatten(), V[j][0].A.flatten())[0] for j in neigh_ids])
            
    else:
        raise Exception('The input {} method for cell-wise velocity confidence calculation is not implemented'
                        ' yet'.format(method))

    adata.obs['confidence'] = confidence

    return adata