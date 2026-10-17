/* Opt-in own-deck v1; legacy ABI is unchanged in generated/. */
#include <stddef.h>
/* K/V contiguous [head=4][context=27][width=16]. Deck rows [2][207]. */
void jepa_context_set_buf(size_t index, void *ptr);
void jepa_context_net(float *z96, float *k0_1728, float *v0_1728,
    float *k1_1728, float *v1_1728, float *value1,
    float *state73, int *ids24, float *feats504, float *mask24, float *deck414);
void jepa_predict4_set_buf(size_t index, void *ptr);
void jepa_predict4_net(float *latent384, float *logits4,
    float *z96, float *k0_1728, float *v0_1728, float *k1_1728, float *v1_1728,
    float *mask26, float *actions248, int *action_ids4, int *horizon1);
