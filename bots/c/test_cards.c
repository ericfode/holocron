/* Tests of the card table (cards.c) filled from a hello's `cards`: make -C bots/c test */
#include "cards.h"
#include "json.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int failed;

#define CHECK(cond)                                                     \
    do {                                                                \
        if (!(cond)) {                                                  \
            fprintf(stderr, "%s:%d: failed: %s\n", __FILE__, __LINE__, #cond); \
            failed++;                                                   \
        }                                                               \
    } while (0)

static const char *internal(const Card *c) { return c ? c->internal : "(none)"; }

/* A hello as the referee sends it: both decks' cards and a token, sorted by internal name. */
static const char HELLO[] =
    "{\"t\":\"hello\",\"v\":1,\"you\":\"p1\",\"seed\":7,\"cards\":["
    "{\"title\":\"Luke Skywalker\",\"subtitle\":\"Faithful Friend\",\"internalName\":\"luke-skywalker#faithful-friend\","
    "\"cost\":6,\"types\":[\"leader\"],\"aspects\":[\"vigilance\",\"heroism\"],\"setId\":{\"set\":\"SOR\",\"number\":5}},"
    "{\"title\":\"Luke Skywalker\",\"subtitle\":\"Jedi Knight\",\"internalName\":\"luke-skywalker#jedi-knight\","
    "\"cost\":6,\"types\":[\"unit\"],\"setId\":{\"set\":\"SOR\",\"number\":51}},"
    "{\"title\":\"Other\",\"internalName\":\"other\",\"cost\":1,\"types\":[\"unit\"],\"setId\":{\"set\":\"SOR\",\"number\":7}},"
    "{\"title\":\"Shield\",\"internalName\":\"shield\",\"types\":[\"token\",\"upgrade\"],\"setId\":{\"set\":\"SOR\"}},"
    "7,"
    "{\"title\":\"Tauntaun Mount\",\"internalName\":\"tauntaun-mount\",\"cost\":3,\"power\":3,\"hp\":4,\"arena\":\"ground\","
    "\"text\":\"Raid 2\",\"keywords\":[\"raid\"],\"types\":[\"unit\"],\"aspects\":[\"aggression\"],"
    "\"setId\":{\"set\":\"IBH\",\"number\":15},"
    "\"setCodes\":[{\"set\":\"IBH\",\"number\":15},{\"set\":\"IBH\",\"number\":28},{\"set\":\"SOR\",\"number\":7}]}"
    "]}";

int main(void) {
    Arena a;
    arena_init(&a, 1 << 10);
    char *text = strdup(HELLO);
    JVal *m = json_parse(text, &a);
    CHECK(m != NULL);
    CHECK(cards_add_all(jget(m, "cards")) == 5); /* the 7 is not a card */
    /* the table keeps its own copies: the message can go */
    arena_reset(&a);
    memset(text, 0, sizeof HELLO);
    free(text);

    const Card *t = card_by_set("IBH_015");
    CHECK(t && !strcmp(t->title, "Tauntaun Mount") && t->cost == 3 && t->power == 3 && t->hp == 4);
    CHECK(t && (t->kw & K_RAID) && t->raid == 2 && (t->types & T_UNIT) && t->aspects[ASP_AGGRESSION] == 1);
    CHECK(card_by_set("IBH_028") == t); /* a reprint code */
    /* SOR_007 is a reprint code of the Tauntaun and Other's own number: the card's own number wins */
    CHECK(!strcmp(internal(card_by_set("SOR_007")), "other"));
    CHECK(card_by_set("SOR_999") == NULL);
    CHECK(card_by_set("SOR_000") == NULL); /* the token has no number */
    /* the first card with a title, in hello's order */
    CHECK(!strcmp(internal(card_by_title("Luke Skywalker")), "luke-skywalker#faithful-friend"));
    CHECK(!strcmp(internal(card_by_internal("luke-skywalker#jedi-knight")), "luke-skywalker#jedi-knight"));
    const Card *s = card_by_internal("shield");
    CHECK(s && (s->types & T_TOKEN) && (s->types & T_UPGRADE));

    /* the next game starts from nothing */
    cards_clear();
    CHECK(card_by_set("IBH_015") == NULL);
    CHECK(card_by_title("Luke Skywalker") == NULL);
    CHECK(card_by_internal("shield") == NULL);
    CHECK(cards_add_all(NULL) == 0);
    JVal *bad = json_parse(strcpy(arena_alloc(&a, 64), "{\"cards\":\"not a list\"}"), &a);
    CHECK(cards_add_all(jget(bad, "cards")) == 0);
    JVal *one = json_parse(strcpy(arena_alloc(&a, 128), "[{\"title\":\"Wampa\",\"internalName\":\"wampa\",\"cost\":4,"
                                                        "\"setId\":{\"set\":\"SOR\",\"number\":38}}]"), &a);
    CHECK(cards_add_all(one) == 1);
    CHECK(!strcmp(internal(card_by_set("SOR_038")), "wampa"));
    CHECK(card_by_set("IBH_015") == NULL);
    cards_clear();
    arena_reset(&a);

    if (failed) {
        fprintf(stderr, "test_cards: %d failed\n", failed);
        return 1;
    }
    printf("test_cards: ok\n");
    return 0;
}
