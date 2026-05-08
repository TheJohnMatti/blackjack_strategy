import pygame
import random
import math

# --- Configuration & Constants ---
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 700
FPS = 60

# Colors
GREEN = (34, 139, 34)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (220, 20, 60)
BLUE = (65, 105, 225)
YELLOW = (255, 215, 0)
GRAY = (200, 200, 200)
DARK_GRAY = (50, 50, 50)

# Pygame Init
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Blackjack Card Counting Pro")
font = pygame.font.SysFont("arial", 22, bold=True)
large_font = pygame.font.SysFont("arial", 40, bold=True)

# --- Game Logic Classes ---

class Card:
    def __init__(self, suit, rank):
        self.suit = suit
        self.rank = rank
        
    def get_value(self):
        if self.rank in ['J', 'Q', 'K']: return 10
        if self.rank == 'A': return 11
        return int(self.rank)

    def get_count_value(self):
        val = self.get_value()
        if val >= 10: return -1
        if val <= 6: return 1
        return 0

    def __str__(self):
        return f"{self.rank}{self.suit}"

class Shoe:
    def __init__(self, num_decks=6, reshuffle_penetration=0.25):
        self.num_decks = num_decks
        self.cards = []
        self.running_count = 0
        self.reshuffle_penetration = reshuffle_penetration
        self.build_shoe()
    
    def get_true_count(self):
        decks_remaining = max(0.25, len(self.cards) / 52)
        return self.running_count / decks_remaining

    def build_shoe(self):
        suits = ['♥', '♦', '♣', '♠']
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        self.cards = [Card(s, r) for _ in range(self.num_decks) for s in suits for r in ranks]
        random.shuffle(self.cards)
        self.running_count = 0

    def draw(self, include_count=True):
        if len(self.cards) < (self.num_decks * 52 * self.reshuffle_penetration):
            self.build_shoe()
        card = self.cards.pop()
        if include_count:
            self.running_count += card.get_count_value()
        return card

# --- Strategy Engine ---

def get_hand_value(hand):
    value = sum(card.get_value() for card in hand)
    aces = sum(1 for card in hand if card.rank == 'A')
    while value > 21 and aces:
        value -= 10
        aces -= 1
    return value

def get_hand_value_and_soft(hand):
    total = sum(card.get_value() for card in hand)
    aces = sum(1 for card in hand if card.rank == 'A')
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total, aces > 0

def is_blackjack(hand):
    return len(hand) == 2 and get_hand_value(hand) == 21

def should_take_insurance(true_count):
    return true_count >= 3

def should_split(p_card, d_val):
    val = p_card.get_value()
    if p_card.rank == 'A': return True
    if val == 10: return False
    if val == 9: return d_val in [2,3,4,5,6,8,9]
    if val == 8: return True
    if val == 7: return d_val in [2,3,4,5,6,7]
    if val == 6: return d_val in [2,3,4,5,6]
    if val == 5: return False
    if val == 4: return d_val in [5,6]
    if val in [2, 3]: return d_val in [2,3,4,5,6,7]
    return False

def get_optimal_action(player_hand, dealer_upcard, true_count, can_split=False):
    """ Returns 'H' (Hit), 'S' (Stand), 'D' (Double), 'P' (Split). """
    d_val = dealer_upcard.get_value()
    p_val, is_soft = get_hand_value_and_soft(player_hand)

    # --- SPLIT LOGIC ---
    if can_split and len(player_hand) == 2 and player_hand[0].get_value() == player_hand[1].get_value():
        if should_split(player_hand[0], d_val):
            return 'P'

    # No need to double 21
    if p_val == 21:
        return 'S'

    # --- DEVIATIONS ---
    if not is_soft and p_val == 16 and d_val == 10 and true_count > 0: return 'S'
    if not is_soft and p_val == 15 and d_val == 10 and true_count >= 4: return 'S'

    # --- SOFT HANDS ---
    if is_soft:
        if p_val >= 19: return 'S'
        if p_val == 18: return 'D' if d_val in [3,4,5,6] else ('S' if d_val in [2,7,8] else 'H')
        if p_val == 17: return 'D' if d_val in [3,4,5,6] else 'H'
        if p_val in [15,16]: return 'D' if d_val in [4,5,6] else 'H'
        if p_val in [13,14]: return 'D' if d_val in [5,6] else 'H'
        return 'H'

    # --- HARD HANDS ---
    if p_val >= 17: return 'S'
    if p_val <= 8: return 'H'
    if p_val == 9: return 'D' if d_val in [3,4,5,6] else 'H'
    if p_val == 10: return 'D' if d_val < 10 else 'H'
    if p_val == 11: return 'D'
    if p_val == 12: return 'S' if d_val in [4,5,6] else 'H'
    if p_val in [13,14,15,16]: return 'S' if d_val in [2,3,4,5,6] else 'H'

    return 'H'

# --- UI Components ---

class Button:
    def __init__(self, x, y, w, h, text, color, hover_color):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.color = color
        self.hover_color = hover_color

    def draw(self, surface):
        mouse_pos = pygame.mouse.get_pos()
        color = self.hover_color if self.rect.collidepoint(mouse_pos) else self.color
        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        pygame.draw.rect(surface, BLACK, self.rect, 2, border_radius=8)
        
        text_surf = font.render(self.text, True, WHITE)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)

    def is_clicked(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos): return True
        return False

def draw_card(surface, card, x, y):
    rect = pygame.Rect(x, y, 70, 100)
    pygame.draw.rect(surface, WHITE, rect, border_radius=5)
    pygame.draw.rect(surface, BLACK, rect, 2, border_radius=5)
    
    color = RED if card.suit in ['♥', '♦'] else BLACK
    text = font.render(str(card), True, color)
    surface.blit(text, (x + 5, y + 5))

# --- Main App ---

class BlackjackApp:
    def __init__(self):
        self.state = "MENU"
        self.shoe = Shoe(num_decks=6)
        self.running = True
        
        # Practice Mode State (Now supports multi-hand splits)
        self.p_hands = [] 
        self.active_hand_idx = 0
        self.d_hand = []
        self.game_over = True
        self.feedback = ""
        self.feedback_color = WHITE
        self.result_texts = []
        self.insurance_available = False
        self.insurance_taken = None
        self.insurance_prompt = ""
        self.show_count = True 
        self.dealer_hole_counted = True

        # Monte Carlo State
        self.mc_bankroll = []
        self.mc_running = False
        self.mc_hands_to_play = 500000
        self.mc_penetration = 0.75

        # Buttons
        self.btn_practice = Button(350, 250, 300, 60, "Practice Mode", BLUE, (100, 150, 255))
        self.btn_mc = Button(350, 350, 300, 60, "Monte Carlo Sim", RED, (255, 100, 100))
        
        # Gameplay Buttons (Moved closer together to fit Split)
        self.btn_hit = Button(250, 600, 100, 50, "Hit", DARK_GRAY, GRAY)
        self.btn_stand = Button(370, 600, 100, 50, "Stand", DARK_GRAY, GRAY)
        self.btn_double = Button(490, 600, 100, 50, "Double", DARK_GRAY, GRAY)
        self.btn_split = Button(610, 600, 100, 50, "Split", DARK_GRAY, GRAY)
        
        self.btn_deal = Button(450, 500, 120, 50, "Deal", BLUE, (100, 150, 255))
        self.btn_back = Button(20, 20, 100, 40, "Back", GRAY, DARK_GRAY)
        self.btn_toggle_count = Button(130, 20, 160, 40, "Toggle Count", GRAY, DARK_GRAY) 
        self.btn_insure_yes = Button(300, 520, 150, 50, "Insurance Yes", DARK_GRAY, GRAY)
        self.btn_insure_no = Button(520, 520, 150, 50, "Insurance No", DARK_GRAY, GRAY)
        
        # Monte Carlo Config Buttons
        self.btn_mc_run = Button(360, 130, 280, 40, "Run Simulation", BLUE, (100, 150, 255))
        self.btn_mc_hands_minus = Button(100, 130, 40, 40, "-", DARK_GRAY, GRAY)
        self.btn_mc_hands_plus = Button(160, 130, 40, 40, "+", DARK_GRAY, GRAY)
        self.btn_mc_pen_minus = Button(740, 130, 40, 40, "-", DARK_GRAY, GRAY)
        self.btn_mc_pen_plus = Button(800, 130, 40, 40, "+", DARK_GRAY, GRAY)

    def start_hand(self):
        self.p_hands = [[self.shoe.draw(), self.shoe.draw()]]
        self.active_hand_idx = 0
        self.d_hand = [self.shoe.draw(), self.shoe.draw(include_count=False)]
        self.dealer_hole_counted = False
        self.game_over = False
        self.feedback = ""
        self.result_texts = []
        self.insurance_available = self.d_hand[0].rank == 'A'
        self.insurance_taken = None
        self.insurance_prompt = self.get_insurance_advice_text() if self.insurance_available else ""
        self.check_dealer_blackjack()

    def reveal_dealer_hole_card(self):
        if not self.dealer_hole_counted and len(self.d_hand) > 1:
            self.shoe.running_count += self.d_hand[1].get_count_value()
            self.dealer_hole_counted = True

    def get_insurance_advice_text(self):
        tc = self.shoe.get_true_count()
        advice = "TAKE" if should_take_insurance(tc) else "DECLINE"
        return f"Insurance advice: {advice} (TC {tc:.2f})"

    def check_dealer_blackjack(self):
        if self.d_hand[0].rank == 'A': return
        if self.d_hand[0].get_value() == 10 and is_blackjack(self.d_hand):
            self.reveal_dealer_hole_card()
            self.game_over = True
            self.evaluate_all_hands()

    def handle_insurance_choice(self, take):
        self.insurance_taken = take
        self.insurance_available = False
        self.insurance_prompt = ""
        if is_blackjack(self.d_hand):
            self.reveal_dealer_hole_card()
            self.game_over = True
            self.evaluate_all_hands()
        elif take:
            self.feedback = "Insurance lost."
            self.feedback_color = RED
        else:
            self.feedback = "Insurance declined."
            self.feedback_color = BLUE

    def can_split_active_hand(self):
        if self.active_hand_idx >= len(self.p_hands): return False
        hand = self.p_hands[self.active_hand_idx]
        return len(hand) == 2 and hand[0].get_value() == hand[1].get_value()

    def process_action(self, action):
        curr_hand = self.p_hands[self.active_hand_idx]
        optimal = get_optimal_action(curr_hand, self.d_hand[0], self.shoe.get_true_count(), can_split=self.can_split_active_hand())
        
        if action == optimal:
            self.feedback = "Correct! (✓)"
            self.feedback_color = BLUE
        else:
            self.feedback = f"Mistake! (X) Correct was: {optimal}"
            self.feedback_color = RED

        if action == 'P':
            # Handle Splitting
            is_ace = curr_hand[0].rank == 'A'
            h1 = [curr_hand[0], self.shoe.draw()]
            h2 = [curr_hand[1], self.shoe.draw()]
            
            self.p_hands[self.active_hand_idx] = h1
            self.p_hands.insert(self.active_hand_idx + 1, h2)
            
            if is_ace:
                # Casino standard: split Aces get one card each and are forced to stand
                self.active_hand_idx += 2
        
        elif action == 'H':
            curr_hand.append(self.shoe.draw())
            if get_hand_value(curr_hand) >= 21:
                self.active_hand_idx += 1
                
        elif action == 'D':
            curr_hand.append(self.shoe.draw())
            self.active_hand_idx += 1
            
        elif action == 'S':
            self.active_hand_idx += 1

        # Check if all hands are played
        if self.active_hand_idx >= len(self.p_hands):
            self.resolve_dealer()

    def resolve_dealer(self):
        self.game_over = True
        self.reveal_dealer_hole_card()
        # Only draw if at least one hand hasn't busted
        needs_dealer_draw = any(get_hand_value(h) <= 21 for h in self.p_hands)
        if needs_dealer_draw:
            while get_hand_value(self.d_hand) < 17:
                self.d_hand.append(self.shoe.draw())
                
        self.evaluate_all_hands()

    def evaluate_all_hands(self):
        self.result_texts = []
        d_val = get_hand_value(self.d_hand)
        dealer_blackjack = is_blackjack(self.d_hand)

        for i, hand in enumerate(self.p_hands):
            p_val = get_hand_value(hand)
            player_blackjack = is_blackjack(hand) and len(self.p_hands) == 1 # Only natural BJ on un-split hands
            
            prefix = f"Hand {i+1}: " if len(self.p_hands) > 1 else ""

            if player_blackjack and dealer_blackjack: res = "Push (Blackjacks)"
            elif player_blackjack: res = "Blackjack! Player wins"
            elif p_val > 21: res = "Player Busts"
            elif dealer_blackjack: res = "Dealer Blackjack"
            elif d_val > 21: res = "Dealer Busts — Player wins"
            elif p_val > d_val: res = "Player Wins"
            elif p_val < d_val: res = "Dealer Wins"
            else: res = "Push"
            
            self.result_texts.append(prefix + res)

        if self.insurance_taken is True:
            ins_res = "Wins" if dealer_blackjack else "Loses"
            self.result_texts.append(f"Insurance {ins_res}")

    def run_monte_carlo(self):
        self.mc_bankroll = [0]
        bankroll = 0
        sim_shoe = Shoe(num_decks=6, reshuffle_penetration=1 - self.mc_penetration)
        total_cards = sim_shoe.num_decks * 52
        reshuffle_point = int(total_cards * (1 - self.mc_penetration))

        for hand_index in range(self.mc_hands_to_play):
            if len(sim_shoe.cards) <= reshuffle_point:
                sim_shoe.build_shoe()

            tc = sim_shoe.get_true_count()
            tc_floor = math.floor(tc) 
            
            if tc_floor <= 0: bet = 1000
            elif tc_floor == 1: bet = 1000
            elif tc_floor == 2: bet = 5000
            elif tc_floor == 3: bet = 5000
            else: bet = 5000

            d_hand = [sim_shoe.draw(), sim_shoe.draw(include_count=False)]
            dealer_hole_counted = False
            dealer_blackjack = is_blackjack(d_hand)

            if d_hand[0].rank == 'A' and should_take_insurance(tc):
                bankroll += bet if dealer_blackjack else (-bet / 2)

            # Queue of hands to process (Hand_Array, Bet_Amount, Is_Split_Ace)
            hands_to_play = [ ([sim_shoe.draw(), sim_shoe.draw()], bet, False) ]
            final_hands = []

            # Process Initial Blackjack
            if is_blackjack(hands_to_play[0][0]):
                if not dealer_hole_counted:
                    sim_shoe.running_count += d_hand[1].get_count_value()
                    dealer_hole_counted = True
                if not dealer_blackjack: bankroll += bet * 1.5
                self.mc_bankroll.append(bankroll)
                continue
            
            if dealer_blackjack:
                if not dealer_hole_counted:
                    sim_shoe.running_count += d_hand[1].get_count_value()
                    dealer_hole_counted = True
                bankroll -= bet
                self.mc_bankroll.append(bankroll)
                continue

            # Play out hands (including splits)
            while hands_to_play:
                curr_hand, curr_bet, is_split_ace = hands_to_play.pop(0)
                
                # Split aces get 1 card and cannot be acted upon further
                if is_split_ace:
                    final_hands.append((curr_hand, curr_bet))
                    continue

                while True:
                    p_val = get_hand_value(curr_hand)
                    if p_val >= 21: break

                    can_split = len(curr_hand) == 2 and curr_hand[0].get_value() == curr_hand[1].get_value()
                    action = get_optimal_action(curr_hand, d_hand[0], sim_shoe.get_true_count(), can_split)

                    if action == 'P':
                        is_ace = curr_hand[0].rank == 'A'
                        h1 = [curr_hand[0], sim_shoe.draw()]
                        h2 = [curr_hand[1], sim_shoe.draw()]
                        # Put back in queue to process
                        hands_to_play.insert(0, (h2, curr_bet, is_ace))
                        hands_to_play.insert(0, (h1, curr_bet, is_ace))
                        break # Exit current hand loop
                    elif action == 'H':
                        curr_hand.append(sim_shoe.draw())
                    elif action == 'D':
                        curr_bet *= 2
                        curr_hand.append(sim_shoe.draw())
                        break
                    elif action == 'S':
                        break

                if action != 'P':
                    final_hands.append((curr_hand, curr_bet))

            # Dealer playout
            d_val = get_hand_value(d_hand)
            if not dealer_hole_counted:
                sim_shoe.running_count += d_hand[1].get_count_value()
                dealer_hole_counted = True
            if any(get_hand_value(h[0]) <= 21 for h in final_hands):
                while get_hand_value(d_hand) < 17:
                    d_hand.append(sim_shoe.draw())
                d_val = get_hand_value(d_hand)

            # Settle final hands
            for h_arr, h_bet in final_hands:
                p_val = get_hand_value(h_arr)
                if p_val > 21: bankroll -= h_bet
                elif d_val > 21 or p_val > d_val: bankroll += h_bet
                elif p_val < d_val: bankroll -= h_bet
                
            self.mc_bankroll.append(bankroll)

        self.mc_running = False

    def draw_menu(self):
        screen.fill(GREEN)
        title = large_font.render("Blackjack Card Counting Pro", True, WHITE)
        screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 100))
        self.btn_practice.draw(screen)
        self.btn_mc.draw(screen)

    def draw_practice(self):
        screen.fill(GREEN)
        self.btn_back.draw(screen)
        self.btn_toggle_count.draw(screen) 
        
        # Stats
        if self.show_count: 
            tc = self.shoe.get_true_count()
            rc = self.shoe.running_count
            stats_txt = font.render(f"RC: {rc}  |  TC: {tc:.2f}", True, WHITE)
            screen.blit(stats_txt, (SCREEN_WIDTH - 250, 20))

        if self.game_over and not self.p_hands:
            self.btn_deal.draw(screen)
            return

        # Draw Dealer Cards
        if self.game_over:
            dealer_label = f"Dealer ({get_hand_value(self.d_hand)})"
        else:
            dealer_label = f"Dealer Upcard: {self.d_hand[0].get_value() if self.d_hand else 0}"
        screen.blit(font.render(dealer_label, True, WHITE), (100, 80))
        for i, card in enumerate(self.d_hand):
            if i == 1 and not self.game_over:
                rect = pygame.Rect(100 + i*80, 110, 70, 100)
                pygame.draw.rect(screen, GRAY, rect, border_radius=5)
            else:
                draw_card(screen, card, 100 + i*80, 110)

        # Draw Player Multiple Hands
        for i, hand in enumerate(self.p_hands):
            # Spread hands out horizontally if split
            x_base = 100 + (i * 200)
            
            # Active hand indicator
            if not self.game_over and i == self.active_hand_idx:
                pygame.draw.rect(screen, YELLOW, (x_base - 10, 270, 180, 220), 3, border_radius=10)

            label = font.render(f"Hand {i+1} ({get_hand_value(hand)})", True, WHITE)
            screen.blit(label, (x_base, 280))
            
            # Stagger cards diagonally to save vertical space
            for j, card in enumerate(hand):
                draw_card(screen, card, x_base + j*25, 320 + j*25)

        # Draw Feedback & Results
        if self.feedback:
            feed_txt = font.render(self.feedback, True, self.feedback_color)
            screen.blit(feed_txt, (SCREEN_WIDTH//2 - feed_txt.get_width()//2, 230))

        if self.result_texts:
            for idx, res in enumerate(self.result_texts):
                res_txt = font.render(res, True, WHITE)
                screen.blit(res_txt, (100, 520 + (idx * 25)))

        if self.insurance_available and self.insurance_taken is None and not self.game_over:
            prompt = font.render(self.insurance_prompt, True, WHITE)
            screen.blit(prompt, (SCREEN_WIDTH//2 - prompt.get_width()//2, 260))
            self.btn_insure_yes.draw(screen)
            self.btn_insure_no.draw(screen)
            return

        if self.game_over:
            self.btn_deal.draw(screen)
        else:
            self.btn_hit.draw(screen)
            self.btn_stand.draw(screen)
            
            # Only show Double/Split if applicable to the ACTIVE hand
            active_hand = self.p_hands[self.active_hand_idx]
            if len(active_hand) == 2:
                self.btn_double.draw(screen)
                if self.can_split_active_hand():
                    self.btn_split.draw(screen)

    def draw_monte_carlo(self):
        screen.fill(DARK_GRAY)
        self.btn_back.draw(screen)

        title = large_font.render("Monte Carlo Simulation", True, WHITE)
        screen.blit(title, (280, 20)) 

        settings_txt = font.render(f"Hands: {self.mc_hands_to_play}   |   Penetration: {int(self.mc_penetration * 100)}%", True, WHITE)
        screen.blit(settings_txt, (50, 85)) 

        self.btn_mc_hands_minus.draw(screen)
        self.btn_mc_hands_plus.draw(screen)
        self.btn_mc_pen_minus.draw(screen)
        self.btn_mc_pen_plus.draw(screen)
        self.btn_mc_run.draw(screen)

        if not self.mc_bankroll or self.mc_running:
            status = "Running..." if self.mc_running else "Ready. Press Run Simulation."
            screen.blit(font.render(status, True, WHITE), (360, 180))
            if self.mc_running:
                pygame.display.flip()
                self.run_monte_carlo()
            return

        # Draw Graph
        graph_rect = pygame.Rect(100, 220, 800, 360)
        pygame.draw.rect(screen, BLACK, graph_rect)
        pygame.draw.rect(screen, WHITE, graph_rect, 2)
        
        min_br = min(self.mc_bankroll)
        max_br = max(self.mc_bankroll)
        br_range = max_br - min_br if max_br != min_br else 1

        points = []
        for i, br in enumerate(self.mc_bankroll):
            x = 100 + (i / len(self.mc_bankroll)) * 800
            y = 580 - ((br - min_br) / br_range) * 360
            points.append((x, y))

        if len(points) > 1:
            pygame.draw.lines(screen, GREEN if self.mc_bankroll[-1] > 0 else RED, False, points, 2)

        zero_y = 580 - ((0 - min_br) / br_range) * 360
        if 220 <= zero_y <= 580:
            pygame.draw.line(screen, GRAY, (100, zero_y), (900, zero_y), 1)

        final_txt = font.render(f"Final Bankroll: ${self.mc_bankroll[-1]}", True, WHITE)
        screen.blit(final_txt, (100, 600))

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            if self.state == "MENU":
                if self.btn_practice.is_clicked(event):
                    self.state = "PRACTICE"
                    self.shoe = Shoe(num_decks=6)
                    self.p_hands = []
                    self.game_over = True
                elif self.btn_mc.is_clicked(event):
                    self.state = "MONTE_CARLO"
                    self.mc_bankroll = [] 
            
            elif self.state == "PRACTICE":
                if self.btn_back.is_clicked(event): self.state = "MENU"
                elif self.btn_toggle_count.is_clicked(event): self.show_count = not self.show_count 
                elif self.insurance_available and self.insurance_taken is None:
                    if self.btn_insure_yes.is_clicked(event): self.handle_insurance_choice(True)
                    elif self.btn_insure_no.is_clicked(event): self.handle_insurance_choice(False)
                elif self.game_over and self.btn_deal.is_clicked(event): self.start_hand()
                elif not self.game_over:
                    if self.btn_hit.is_clicked(event): self.process_action('H')
                    elif self.btn_stand.is_clicked(event): self.process_action('S')
                    elif self.btn_double.is_clicked(event) and len(self.p_hands[self.active_hand_idx]) == 2: 
                        self.process_action('D')
                    elif self.btn_split.is_clicked(event) and self.can_split_active_hand():
                        self.process_action('P')

            elif self.state == "MONTE_CARLO":
                if self.btn_back.is_clicked(event): self.state = "MENU"
                elif self.btn_mc_run.is_clicked(event) and not self.mc_running:
                    self.mc_bankroll = []
                    self.mc_running = True
                elif self.btn_mc_hands_minus.is_clicked(event):
                    self.mc_hands_to_play = max(1000, self.mc_hands_to_play - 1000)
                elif self.btn_mc_hands_plus.is_clicked(event):
                    self.mc_hands_to_play = min(500000, self.mc_hands_to_play + 10000)
                elif self.btn_mc_pen_minus.is_clicked(event):
                    self.mc_penetration = max(0.60, self.mc_penetration - 0.05)
                elif self.btn_mc_pen_plus.is_clicked(event):
                    self.mc_penetration = min(0.90, self.mc_penetration + 0.05)

    def run(self):
        clock = pygame.time.Clock()
        while self.running:
            self.handle_events()
            if self.state == "MENU": self.draw_menu()
            elif self.state == "PRACTICE": self.draw_practice()
            elif self.state == "MONTE_CARLO": self.draw_monte_carlo()
            pygame.display.flip()
            clock.tick(FPS)
        pygame.quit()

if __name__ == "__main__":
    app = BlackjackApp()
    app.run()