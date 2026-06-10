ALGORITHM: Maritime Vehicle Routing using Genetic Algorithm

INPUT: 
  S: Set of available ships with capacity C_s
  P: Set of port locations with TEU demands D_p
  PopSize: Size of the population (default: 20)
  MaxGen: Maximum number of generations (default: 50)
  MutRate: Probability of mutation (default: 0.15)
  Depot: Starting and ending port location

OUTPUT: 
  BestRouteSet: A set of optimized ship routes with minimized operational cost

BEGIN
  // Step 1: Initialization
  Population = GenerateInitialPopulation(PopSize, S, P, Depot)
  BestSolution = NULL
  History = []

  // Step 2: Evolution Loop
  FOR generation = 1 TO MaxGen DO
      
      // Step 2.1: Fitness Evaluation
      FOR EACH individual IN Population DO
          TotalCost = 0
          Penalty = 0
          
          FOR EACH route IN individual DO
              Cost = CalculateRouteCost(route)
              TotalLoad = Sum(D_p for p in route)
              
              IF TotalLoad > C_s THEN
                  Penalty = Penalty + (TotalLoad - C_s) * PenaltyWeight
              END IF
              
              TotalCost = TotalCost + Cost + Penalty
          END FOR
          
          individual.Fitness = TotalCost
      END FOR
      
      // Step 2.2: Track Best Solution
      CurrentBest = FindIndividualWithMinFitness(Population)
      History.Append(CurrentBest.Fitness)
      IF CurrentBest.Fitness < BestSolution.Fitness THEN
          BestSolution = CurrentBest
      END IF
      
      // Step 2.3: Reproduction (Crossover & Mutation)
      NewPopulation = []
      NewPopulation.Append(CurrentBest) // Elitism

      WHILE Size(NewPopulation) < PopSize DO
          Parent1, Parent2 = TournamentSelection(Population)
          Child = OrderedCrossover(Parent1, Parent2)
          
          IF Random(0, 1) < MutRate THEN
              Child = SwapMutation(Child)
          END IF
          
          NewPopulation.Append(Child)
      END WHILE
      
      Population = NewPopulation
  END FOR
  
  RETURN BestSolution, History
END
